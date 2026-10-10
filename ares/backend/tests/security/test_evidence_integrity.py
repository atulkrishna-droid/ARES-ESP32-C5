"""Security Audit Tests: Forensic Evidence & Chain of Custody Integrity (Section 16)."""
import hashlib
import pytest
from app.models.case import Case
from app.models.device import Device
from app.models.assessment import Assessment
from app.services.evidence_service import EvidenceService
from app.core.exceptions import ForensicIntegrityException


def test_dual_hashing_and_tamper_detection(db_session, seeded_users):
    """Verify SHA-256 and SHA-512 dual hashing and detection of modified evidence."""
    admin = seeded_users["admin"]
    case = Case(case_number="CASE-FORENSIC-01", title="Forensic Case", created_by=admin.id)
    dev = Device(device_uuid="FORENSIC-DEV-01", authorization_status="ACTIVE")
    db_session.add_all([case, dev])
    db_session.commit()

    assessment = Assessment(
        case_id=case.id,
        target_device_id=dev.id,
        assessment_type="WIFI_DISCOVERY",
        status="RUNNING",
        created_by=admin.id,
    )
    db_session.add(assessment)
    db_session.commit()

    raw_payload = b"PCAP_OBSERVATION_FRAME_DATA_1234567890_FORENSIC_ACQUISITION"
    expected_sha256 = hashlib.sha256(raw_payload).hexdigest()
    expected_sha512 = hashlib.sha512(raw_payload).hexdigest()

    # Collect and store evidence
    evidence = EvidenceService.create_evidence(
        db=db_session,
        case_id=case.id,
        assessment_id=assessment.id,
        device_id=dev.id,
        file_name="capture.pcap",
        raw_bytes=raw_payload,
        collected_by=admin.id,
    )

    assert evidence.sha256_hash == expected_sha256
    assert evidence.sha512_hash == expected_sha512
    assert len(evidence.custody_entries) == 1
    assert evidence.custody_entries[0].action == "COLLECTED"

    # Verify untampered evidence passes verification
    assert EvidenceService.verify_evidence(db_session, evidence.id, raw_payload) is True

    # Tamper with the bytes -> Must fail verification!
    tampered_bytes = raw_payload + b"_ATTACKER_INJECTED_BYTES"
    with pytest.raises(ForensicIntegrityException) as exc_info:
        EvidenceService.verify_evidence(db_session, evidence.id, tampered_bytes)
    assert "forensic integrity violation" in str(exc_info.value).lower()
