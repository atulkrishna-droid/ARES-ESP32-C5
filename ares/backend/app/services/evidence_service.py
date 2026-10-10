"""Forensics Evidence and Cryptographic Chain of Custody Service."""
import base64
import os
from datetime import datetime, timezone
from typing import Any, List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import ChainOfCustodyEventType, EvidenceType
from app.core.exceptions import (
    ForensicIntegrityException,
    ResourceNotFoundException,
    StorageException,
)
from app.core.security import canonical_json_bytes, sha256_hash, sha512_hash
from app.models.case import Case
from app.models.evidence import ChainOfCustodyEvent, Evidence
from app.schemas.evidence import EvidenceCreateRequest
from app.services.audit_service import AuditService


class EvidenceService:
    @staticmethod
    def _ensure_storage_dir() -> str:
        os.makedirs(settings.EVIDENCE_STORAGE_PATH, exist_ok=True)
        return settings.EVIDENCE_STORAGE_PATH

    @classmethod
    def create_evidence(
        cls,
        db: Session,
        request: Optional[EvidenceCreateRequest] = None,
        actor_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Evidence:
        if request is not None:
            case_id = request.case_id
            assessment_id = request.assessment_id
            device_id = request.device_id
            name = request.name
            description = request.description
            source = request.source
            raw_content = request.raw_content
            evidence_type = request.type.value if hasattr(request.type, "value") else str(request.type)
            collector_id = actor_id
        else:
            case_id = kwargs.get("case_id")
            assessment_id = kwargs.get("assessment_id")
            device_id = kwargs.get("device_id")
            name = kwargs.get("file_name") or kwargs.get("name") or "unnamed_evidence.bin"
            description = kwargs.get("description")
            source = kwargs.get("source") or "ESP32_C5"
            raw_content = kwargs.get("raw_bytes") or kwargs.get("raw_content") or b""
            evidence_type = kwargs.get("type", EvidenceType.DEVICE_METADATA.value)
            if hasattr(evidence_type, "value"):
                evidence_type = evidence_type.value
            collector_id = kwargs.get("collected_by") or actor_id

        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ResourceNotFoundException("Target Case not found.")

        # Decode or normalize content bytes
        if isinstance(raw_content, bytes):
            content_bytes = raw_content
        else:
            try:
                content_bytes = base64.b64decode(raw_content, validate=True)
            except Exception:
                content_bytes = str(raw_content).encode("utf-8")

        calc_sha256 = sha256_hash(content_bytes)
        calc_sha512 = sha512_hash(content_bytes)
        size_bytes = len(content_bytes)

        # Enforce size limits
        max_bytes = settings.MAX_EVIDENCE_SIZE_MB * 1024 * 1024
        if size_bytes > max_bytes:
            raise StorageException(f"Evidence payload size exceeds maximum allowed limit of {settings.MAX_EVIDENCE_SIZE_MB}MB.")

        # Sanitize metadata display name against path traversal
        clean_name = os.path.basename(name).replace("\x00", "")
        if not clean_name:
            clean_name = "unnamed_evidence.bin"

        # Save to local filesystem abstraction using cryptographic hash as filename
        storage_dir = cls._ensure_storage_dir()
        filename = f"{calc_sha256}.bin"
        file_path = os.path.abspath(os.path.join(storage_dir, filename))

        with open(file_path, "wb") as f:
            f.write(content_bytes)

        now = datetime.now(timezone.utc)
        evidence = Evidence(
            case_id=case_id,
            assessment_id=assessment_id,
            device_id=device_id,
            type=evidence_type,
            name=clean_name,
            description=description,
            source=source,
            path_reference=file_path,
            sha256=calc_sha256,
            sha512=calc_sha512,
            size_bytes=size_bytes,
            collected_at=now,
            collected_by=collector_id,
            created_at=now,
        )
        db.add(evidence)
        db.flush()

        # Create initial chain of custody event
        init_event_content = {
            "evidence_id": evidence.id,
            "event_type": ChainOfCustodyEventType.COLLECTED.value,
            "actor_id": collector_id,
            "sha256": calc_sha256,
            "timestamp": now.isoformat(),
        }
        init_event_hash = sha256_hash(canonical_json_bytes(init_event_content))

        custody_event = ChainOfCustodyEvent(
            evidence_id=evidence.id,
            actor_id=collector_id,
            event_type=ChainOfCustodyEventType.COLLECTED.value,
            timestamp=now,
            description=f"Evidence collected and secured with SHA-256 integrity hash: {calc_sha256}",
            previous_hash=None,
            event_hash=init_event_hash,
        )
        db.add(custody_event)
        db.commit()
        db.refresh(evidence)

        AuditService.record_event(
            db=db,
            action="EVIDENCE_CREATED",
            resource_type="EVIDENCE",
            resource_id=evidence.id,
            actor_id=collector_id,
            metadata={"case_id": case.id, "sha256": calc_sha256, "size_bytes": size_bytes},
        )
        return evidence

    @classmethod
    def verify_evidence(cls, db: Session, evidence_id: str, raw_bytes: bytes) -> bool:
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            raise ResourceNotFoundException(f"Evidence '{evidence_id}' not found.")

        calc_sha256 = sha256_hash(raw_bytes)
        calc_sha512 = sha512_hash(raw_bytes)

        if calc_sha256 != evidence.sha256 or (evidence.sha512 and calc_sha512 != evidence.sha512):
            raise ForensicIntegrityException(
                f"Forensic integrity violation: Evidence '{evidence_id}' hash mismatch (calculated={calc_sha256}, stored={evidence.sha256})"
            )
        return True

    @classmethod
    def record_custody_action(
        cls, db: Session, evidence_id: str, actor_id: str, event_type: ChainOfCustodyEventType, description: str
    ) -> ChainOfCustodyEvent:
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            raise ResourceNotFoundException("Evidence item not found.")

        # Get last custody event hash
        last_event = (
            db.query(ChainOfCustodyEvent)
            .filter(ChainOfCustodyEvent.evidence_id == evidence_id)
            .order_by(ChainOfCustodyEvent.timestamp.desc(), ChainOfCustodyEvent.id.desc())
            .first()
        )
        prev_hash = last_event.event_hash if last_event else None

        now = datetime.now(timezone.utc)
        event_content = {
            "evidence_id": evidence.id,
            "event_type": event_type.value,
            "actor_id": actor_id,
            "previous_hash": prev_hash,
            "timestamp": now.isoformat(),
            "description": description,
        }
        event_hash = sha256_hash(canonical_json_bytes(event_content))

        custody_event = ChainOfCustodyEvent(
            evidence_id=evidence.id,
            actor_id=actor_id,
            event_type=event_type.value,
            timestamp=now,
            description=description,
            previous_hash=prev_hash,
            event_hash=event_hash,
        )
        db.add(custody_event)
        db.commit()
        db.refresh(custody_event)
        return custody_event
