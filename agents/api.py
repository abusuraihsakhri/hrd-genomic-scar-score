"""FastAPI service for the optional demo workflow and HRD component arithmetic."""
import hmac
import os

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from hrd_scar import calculate_metrics
from .base import AuditLogger, SecurityException
from .models import SystemTaskPayload
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")
app = FastAPI(
    title="HRD Genomic Scar Score API",
    description="Research-only genomic scar component sum and separate demonstration audit workflow",
    version="3.0.1",
)


class ChatRequest(BaseModel):
    query: str


class ScoreRequest(BaseModel):
    loh: int
    tai: int
    lst: int


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "hrd-genomic-scar-score", "version": "3.0.1"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "audit_chain_verified": AuditLogger.verify_integrity(),
    }


@app.post("/api/score")
def api_score(payload: ScoreRequest):
    try:
        return calculate_metrics(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    try:
        return supervisor.process_task(payload).to_dict()
    except SecurityException as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        return {"response": supervisor.query_supervisory_chat(req.query)}
    except SecurityException as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/audit/logs")
def api_audit_logs(authorization: str | None = Header(default=None)):
    token = os.getenv("AUDIT_LOG_API_TOKEN", "")
    expected = "Bearer " + token
    if not token or not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=403, detail="Audit log access disabled or unauthorized")
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
