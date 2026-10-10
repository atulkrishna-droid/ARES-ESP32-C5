"""Tamper-Evident Audit Logging Service."""
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import canonical_json_bytes, sha256_hash
from app.models.audit_log import AuditLog


class AuditService:
    GENESIS_HASH: Optional[str] = None

    @classmethod
    def log_event(
        cls,
        db: Session,
        action: str,
        actor_id: Optional[str] = None,
        resource_type: str = "SYSTEM",
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> AuditLog:
        return cls.record_event(
            db=db,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=actor_id,
            metadata=details or metadata or {},
            **kwargs,
        )

    @staticmethod
    def get_latest_event_hash(db: Session) -> Optional[str]:
        latest = db.query(AuditLog).order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).first()
        return latest.event_hash if latest else None

    @classmethod
    def record_event(
        cls,
        db: Session,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Record an immutable audit log entry cryptographically linked to the previous entry."""
        meta = metadata or {}
        previous_hash = cls.get_latest_event_hash(db)

        now = datetime.now(timezone.utc)
        ts_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        canonical_content = {
            "action": action,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id else None,
            "actor_id": str(actor_id) if actor_id else None,
            "timestamp": ts_str,
            "metadata": meta,
            "previous_hash": previous_hash or "GENESIS_BLOCK_00000000000000000000000000000000000000000000000000000000",
        }

        # Calculate cryptographically chained event hash
        payload_bytes = canonical_json_bytes(canonical_content)
        event_hash = sha256_hash(payload_bytes)

        log_entry = AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            timestamp=now,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json=meta,
            previous_event_hash=previous_hash,
            event_hash=event_hash,
        )

        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @classmethod
    def verify_chain(cls, db: Session) -> Tuple[bool, int, Optional[str], Optional[str]]:
        """
        Verify mathematical integrity of the entire audit chain.
        Returns: (is_valid, total_events, invalid_event_id, last_verified_event_id)
        """
        events = db.query(AuditLog).order_by(AuditLog.timestamp.asc(), AuditLog.id.asc()).all()
        if not events:
            return True, 0, None, None

        expected_previous_hash = None
        last_verified_id = None

        for event in events:
            # Check previous hash link
            if event.previous_event_hash != expected_previous_hash:
                return False, len(events), event.id, last_verified_id

            if isinstance(event.timestamp, datetime):
                event_ts_str = event.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                event_ts_str = str(event.timestamp)

            canonical_content = {
                "action": event.action,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "actor_id": event.actor_id,
                "timestamp": event_ts_str,
                "metadata": event.metadata_json or {},
                "previous_hash": expected_previous_hash or "GENESIS_BLOCK_00000000000000000000000000000000000000000000000000000000",
            }

            calculated_hash = sha256_hash(canonical_json_bytes(canonical_content))
            if calculated_hash != event.event_hash:
                return False, len(events), event.id, last_verified_id

            expected_previous_hash = event.event_hash
            last_verified_id = event.id

        return True, len(events), None, last_verified_id

    @classmethod
    def verify_chain_integrity(cls, db: Session) -> Dict[str, Any]:
        is_valid, count, invalid_id, last_id = cls.verify_chain(db)
        return {
            "is_valid": is_valid,
            "verified_events": count if is_valid else 0,
            "total_events": count,
            "invalid_event_id": invalid_id,
            "broken_at_sequence": invalid_id,
        }
