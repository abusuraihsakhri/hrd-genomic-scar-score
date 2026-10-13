"""Demo supervisor orchestration and audit logging."""
import json
import uuid
from typing import Any

from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, AgentAlert, ConsensusDossier, UrgencyLevel, SystemIntegrityStatus
from .workers import InvariantQCWorker, SafetyEscalationWorker, ProtocolConformanceWorker
from .llm_factory import LLMFactory


class SystemSupervisor:
    """Coordinates deterministic demo policy workers; not clinical triage."""

    def __init__(self, model_provider: str = "mock"):
        self.qc_worker = InvariantQCWorker()
        self.safety_worker = SafetyEscalationWorker()
        self.conformance_worker = ProtocolConformanceWorker()
        self.llm = LLMFactory.create(model_provider, system_name="HRD Genomic Scar Score")
        self.dossier_registry: dict[str, ConsensusDossier] = {}

    def process_task(self, payload: SystemTaskPayload, actor: str = "SystemSupervisor") -> ConsensusDossier:
        for value in (
            payload.task_id,
            payload.target_identifier,
            payload.status_descriptor,
            json.dumps(payload.attributes, default=str),
        ):
            PHIGuard.assert_no_phi(value)

        all_alerts: list[AgentAlert] = []
        all_alerts.extend(self.qc_worker.evaluate(payload))
        all_alerts.extend(self.safety_worker.evaluate(payload))
        all_alerts.extend(self.conformance_worker.evaluate(payload))
        critical = sum(a.urgency == UrgencyLevel.CRITICAL_STAT for a in all_alerts)
        elevated = sum(a.urgency == UrgencyLevel.ELEVATED for a in all_alerts)
        if critical:
            urgency = UrgencyLevel.CRITICAL_STAT
            integrity = SystemIntegrityStatus.RECALIBRATION_REQUIRED
        elif elevated:
            urgency = UrgencyLevel.ELEVATED
            integrity = SystemIntegrityStatus.DISCORDANT
        else:
            urgency = UrgencyLevel.ROUTINE
            integrity = SystemIntegrityStatus.VALIDATED

        signed = AuditLogger.log(
            actor=actor,
            actor_tier="supervisor",
            event_type="TASK_EVALUATION_COMPLETED",
            details={
                "task_id": payload.task_id,
                "target_identifier": payload.target_identifier,
                "overall_urgency": urgency.value,
                "total_alerts": len(all_alerts),
            },
        )
        dossier = ConsensusDossier(
            dossier_id=f"DOSSIER-{uuid.uuid4().hex[:8].upper()}",
            task_id=payload.task_id,
            target_identifier=payload.target_identifier,
            overall_urgency=urgency,
            integrity_status=integrity,
            total_alerts=len(all_alerts),
            critical_alerts_count=critical,
            alerts=all_alerts,
            consensus_summary=(
                f"Demonstration rule checks completed: {urgency.value}; "
                f"{len(all_alerts)} alerts. Not a clinical assessment."
            ),
            audit_hash=signed["current_hash"],
        )
        self.dossier_registry[dossier.dossier_id] = dossier
        return dossier

    def query_supervisory_chat(self, query: str) -> str:
        PHIGuard.assert_no_phi(query)
        return self.llm.invoke(query)
