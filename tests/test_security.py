import pytest

from agents.base import AuditTrail, PHIGuard, SecurityException
from agents.llm_factory import LLMFactory
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor


def test_hmac_detects_modified_signed_fields():
    audit = AuditTrail(secret_key="test-key-only")
    entry = audit.log("tester", "demo", "TASK", {"value": 1})
    assert len(entry["current_hash"]) == 64
    assert audit.verify_integrity()
    audit.logs[0]["event_type"] = "FORGED"
    assert not audit.verify_integrity()


def test_hmac_detects_forged_hash():
    audit = AuditTrail(secret_key="test-key-only")
    audit.log("tester", "demo", "TASK", {"value": 1})
    audit.logs[0]["current_hash"] = "0" * 64
    assert not audit.verify_integrity()


def test_returned_trail_does_not_allow_external_mutation():
    audit = AuditTrail(secret_key="test-key-only")
    audit.log("tester", "demo", "TASK", {"value": 1})
    audit.get_trail()[0]["actor"] = "intruder"
    assert audit.verify_integrity()


def test_phi_check_extended_to_payload_attributes():
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="T-01", target_identifier="S-01", primary_metric=1,
        attributes={"notes": "MRN-123456"},
    )
    with pytest.raises(SecurityException):
        supervisor.process_task(payload)


def test_mock_reports_its_real_capabilities():
    mock = LLMFactory.create("mock")
    assert "No clinical or scientific analysis" in mock.invoke("test")
    with pytest.raises(ValueError, match="Unsupported"):
        LLMFactory.create("openai")


def test_api_audit_logs_requires_token(monkeypatch):
    from agents.api import api_audit_logs
    from fastapi import HTTPException
    monkeypatch.delenv("AUDIT_LOG_API_TOKEN", raising=False)
    with pytest.raises(HTTPException) as exc:
        api_audit_logs(authorization="Bearer test")
    assert exc.value.status_code == 403
    monkeypatch.setenv("AUDIT_LOG_API_TOKEN", "safe-test-token")
    with pytest.raises(HTTPException):
        api_audit_logs(authorization="Bearer wrong")
    assert api_audit_logs(authorization="Bearer safe-test-token")["verified"] is True


def test_api_score_only_uses_three_counts():
    from agents.api import ScoreRequest, api_score
    assert api_score(ScoreRequest(loh=5, tai=6, lst=7))["score"] == 18
