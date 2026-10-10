"""Tests for the Tamper-Evident Cryptographic Audit Ledger."""
import pytest
from app.models.audit_log import AuditLog
from app.services.audit_service import AuditService


def test_audit_log_cryptographic_chaining(db_session, seeded_users):
    admin = seeded_users["admin"]

    # 1. Record series of events
    e1 = AuditService.record_event(
        db=db_session,
        action="TEST_ACTION_1",
        resource_type="CASE",
        resource_id="C-001",
        actor_id=admin.id,
    )
    assert e1.previous_event_hash is None
    assert e1.event_hash is not None

    e2 = AuditService.record_event(
        db=db_session,
        action="TEST_ACTION_2",
        resource_type="DEVICE",
        resource_id="D-001",
        actor_id=admin.id,
    )
    assert e2.previous_event_hash == e1.event_hash

    e3 = AuditService.record_event(
        db=db_session,
        action="TEST_ACTION_3",
        resource_type="ASSESSMENT",
        resource_id="A-001",
        actor_id=admin.id,
    )
    assert e3.previous_event_hash == e2.event_hash

    # 2. Verify pristine chain
    is_valid, total, invalid_id, last_verified = AuditService.verify_chain(db_session)
    assert is_valid is True
    assert total >= 3
    assert invalid_id is None

    # 3. Simulate tamper event in database
    e2.action = "MALICIOUSLY_ALTERED_ACTION"
    db_session.commit()

    # 4. Verification must detect tampered link
    is_valid_tampered, _, invalid_id, _ = AuditService.verify_chain(db_session)
    assert is_valid_tampered is False
    assert invalid_id == e2.id
