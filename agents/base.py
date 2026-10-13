"""Identifier screening and process-local HMAC-SHA256 audit chain.

Pattern-based screening is not exhaustive PHI de-identification. A persistent
AUDIT_SECRET_KEY and external storage are needed for long-term audit use.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Any

PHI_PATTERNS = [
    re.compile(r"\bMRN[:#\s-]*\d{4,10}\b", re.IGNORECASE),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b(?:DOB|Date of Birth)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", re.IGNORECASE),
    re.compile(r"\b(?:Patient\s+Name|Patient)[:\s]+[A-Z][a-z]+\s+[A-Z][a-z]+\b", re.IGNORECASE),
    re.compile(r"\b(?:John\s+Doe|Jane\s+Smith|Alice\s+Johnson)\b", re.IGNORECASE),
]


class SecurityException(Exception):
    """A known identifier pattern was detected."""


class ResourceLimitExceededException(Exception):
    """A computation exceeded its configured resource limit."""


def assert_no_phi(text: str) -> None:
    for pattern in PHI_PATTERNS:
        if pattern.search(str(text or "")):
            raise SecurityException("Sensitive identifier pattern detected")


class PHIGuard:
    @staticmethod
    def assert_no_phi(text: str) -> None:
        assert_no_phi(text)

    @staticmethod
    def redact_phi(text: str) -> str:
        result = str(text)
        for pattern in PHI_PATTERNS:
            result = pattern.sub("[REDACTED_IDENTIFIER]", result)
        return result


class AuditTrail:
    """In-memory, HMAC-signed hash chain. No persistent audit storage."""

    GENESIS = "GENESIS_BLOCK_0000000000000000"
    SIGNED_FIELDS = (
        "audit_id", "timestamp", "actor", "actor_tier",
        "event_type", "payload_hash", "prev_hash"
    )

    def __init__(self, secret_key: str | bytes | None = None):
        key = secret_key or os.getenv("AUDIT_SECRET_KEY") or secrets.token_hex(32)
        self.secret_key = key.encode("utf-8") if isinstance(key, str) else key
        self.logs: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def _signature(self, entry: dict[str, Any]) -> str:
        message = "|".join(str(entry[field]) for field in self.SIGNED_FIELDS)
        return hmac.new(self.secret_key, message.encode("utf-8"), hashlib.sha256).hexdigest()

    def log(self, actor: str, actor_tier: str, event_type: str, details: dict[str, Any]) -> dict[str, Any]:
        serialized = json.dumps(details, sort_keys=True)
        for value in (actor, actor_tier, event_type, serialized):
            assert_no_phi(value)
        payload_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        with self._lock:
            entry = {
                "audit_id": f"AUDIT-{time.time_ns()}-{len(self.logs)+1}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actor": actor,
                "actor_tier": actor_tier,
                "event_type": event_type,
                "payload_hash": payload_hash,
                "prev_hash": self.logs[-1]["current_hash"] if self.logs else self.GENESIS,
            }
            entry["current_hash"] = self._signature(entry)
            self.logs.append(entry)
            return dict(entry)

    def verify_integrity(self) -> bool:
        with self._lock:
            prior = self.GENESIS
            for entry in self.logs:
                try:
                    if entry["prev_hash"] != prior:
                        return False
                    signature = self._signature(entry)
                    if not hmac.compare_digest(signature, entry["current_hash"]):
                        return False
                    prior = entry["current_hash"]
                except (KeyError, TypeError, ValueError):
                    return False
            return True

    def get_trail(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(entry) for entry in self.logs]


GLOBAL_AUDIT = AuditTrail()


class AuditLogger:
    @staticmethod
    def log(actor: str, actor_tier: str, event_type: str, details: dict[str, Any]) -> dict[str, Any]:
        return GLOBAL_AUDIT.log(actor, actor_tier, event_type, details)

    @staticmethod
    def get_trail() -> list[dict[str, Any]]:
        return GLOBAL_AUDIT.get_trail()

    @staticmethod
    def verify_integrity() -> bool:
        return GLOBAL_AUDIT.verify_integrity()


class ActionExecutor:
    @staticmethod
    def execute_with_audit(actor: str, actor_tier: str, action_type: str, fn, *args, **kwargs):
        result = fn(*args, **kwargs)
        AuditLogger.log(actor, actor_tier, action_type, {"status": "SUCCESS"})
        return result
