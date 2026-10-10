"""Tests for Forensics Evidence hashing and Chain of Custody."""
import os
import pytest
from app.core.constants import ChainOfCustodyEventType, EvidenceType
from app.models.case import Case
from app.schemas.evidence import EvidenceCreateRequest
from app.services.evidence_service import EvidenceService


def test_evidence_creation_hashing_and_custody(db_session, seeded_users):
    admin = seeded_users["admin"]
    case = Case(case_number="CASE-2026-EVID", title="Evidence Case", created_by=admin.id)
    db_session.add(case)
    db_session.commit()

    sample_content = "AUTHENTICATED_FORENSIC_TELEMETRY_SAMPLE_DATA_2026"
    req = EvidenceCreateRequest(
        case_id=case.id,
        name="mobile_security_dump.json",
        type=EvidenceType.DEVICE_METADATA,
        source="ANDROID_AGENT",
        raw_content=sample_content,
    )

    evidence = EvidenceService.create_evidence(db_session, req, actor_id=admin.id)
    assert evidence.id is not None
    assert evidence.sha256 is not None
    assert len(evidence.sha256) == 64
    assert os.path.exists(evidence.path_reference)

    # Initial custody event must exist
    assert len(evidence.custody_events) == 1
    assert evidence.custody_events[0].event_type == "COLLECTED"

    # Record secondary custody action
    event2 = EvidenceService.record_custody_action(
        db_session,
        evidence_id=evidence.id,
        actor_id=admin.id,
        event_type=ChainOfCustodyEventType.VIEWED,
        description="Analyst reviewed forensic dump in secure viewer",
    )
    assert event2.previous_hash == evidence.custody_events[0].event_hash
