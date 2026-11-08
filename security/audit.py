"""Append-only application audit helper with a SHA-256 hash chain.

This is tamper-evident (not tamper-proof): a database administrator who can
rewrite the complete chain can still forge it. Export/anchor hashes externally
for stronger assurance in production.
"""
import hashlib
import json
from datetime import datetime, timezone
from flask import request, has_request_context
from extensions import db
from models.audit_log import AuditLog


def _normalized_iso(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()

def append_audit(actor_id, action, outcome, document_id=None, target_user_id=None, details=None):
    previous = AuditLog.query.order_by(AuditLog.id.desc()).with_for_update().first()
    previous_hash = previous.event_hash if previous else "GENESIS"
    created_at = datetime.now(timezone.utc)
    remote_ip = request.remote_addr if has_request_context() else None
    payload = {
        "actor_id": actor_id, "document_id": document_id,
        "target_user_id": target_user_id, "action": action,
        "outcome": outcome, "ip_address": remote_ip,
        "created_at": _normalized_iso(created_at), "details": details or {},
        "previous_hash": previous_hash,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    row = AuditLog(
        actor_id=actor_id, document_id=document_id, target_user_id=target_user_id,
        action=action, outcome=outcome, ip_address=remote_ip,
        created_at=created_at, details=details or {}, previous_hash=previous_hash,
        event_hash=digest,
    )
    db.session.add(row)
    return row


def verify_audit_chain():
    rows = AuditLog.query.order_by(AuditLog.id.asc()).all()
    previous_hash = "GENESIS"
    for row in rows:
        payload = {
            "actor_id": row.actor_id, "document_id": row.document_id,
            "target_user_id": row.target_user_id, "action": row.action,
            "outcome": row.outcome, "ip_address": row.ip_address,
            "created_at": _normalized_iso(row.created_at), "details": row.details or {},
            "previous_hash": previous_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if row.previous_hash != previous_hash or row.event_hash != expected:
            return False, row.id
        previous_hash = row.event_hash
    return True, None
