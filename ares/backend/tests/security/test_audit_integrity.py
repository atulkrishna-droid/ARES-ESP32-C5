"""Security Audit Tests: Cryptographic Audit Ledger Integrity (Section 17)."""
import pytest
from app.models.audit_log import AuditLog
from app.services.audit_service import AuditService


def test_audit_hash_chain_genesis_to_n(db_session, seeded_users):
    """Verify that events chain sequentially from GENESIS."""
    admin = seeded_users["admin"]

    e1 = AuditService.log_event(db_session, "CASE_CREATE", actor_id=admin.id, details={"step": 1})
    e2 = AuditService.log_event(db_session, "DEVICE_ENROLL", actor_id=admin.id, details={"step": 2})
    e3 = AuditService.log_event(db_session, "ASSESSMENT_START", actor_id=admin.id, details={"step": 3})

    assert e1.previous_hash == AuditService.GENESIS_HASH
    assert e2.previous_hash == e1.current_hash
    assert e3.previous_hash == e2.current_hash

    # Verify chain passes
    result = AuditService.verify_chain_integrity(db_session)
    assert result["is_valid"] is True
    assert result["verified_events"] >= 3


def test_tampered_event_detected(db_session, seeded_users):
    """Verify that tampering with any field in an audit entry invalidates the chain."""
    admin = seeded_users["admin"]

    AuditService.log_event(db_session, "EVT_1", actor_id=admin.id, details={"auth": "ok"})
    e2 = AuditService.log_event(db_session, "EVT_2", actor_id=admin.id, details={"auth": "ok"})
    AuditService.log_event(db_session, "EVT_3", actor_id=admin.id, details={"auth": "ok"})

    # Malicious direct modification of e2 details without recomputing hashes
    e2.details = {"auth": "tampered_by_attacker"}
    db_session.commit()

    # Verification must FAIL
    result = AuditService.verify_chain_integrity(db_session)
    assert result["is_valid"] is False
    assert result["broken_at_sequence"] == e2.sequence_number


def test_deleted_event_breaks_chain(db_session, seeded_users):
    """Verify that deleting an intermediate event breaks the previous_hash link."""
    admin = seeded_users["admin"]

    AuditService.log_event(db_session, "STEP_A", actor_id=admin.id)
    e_mid = AuditService.log_event(db_session, "STEP_B", actor_id=admin.id)
    e_last = AuditService.log_event(db_session, "STEP_C", actor_id=admin.id)

    # Maliciously delete middle event
    db_session.delete(e_mid)
    db_session.commit()

    result = AuditService.verify_chain_integrity(db_session)
    assert result["is_valid"] is False
