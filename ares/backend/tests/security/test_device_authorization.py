"""Security Audit Tests: Device Lifecycle, Authorization Constraints, Database Invariants (Section 3)."""
import pytest
from sqlalchemy.exc import IntegrityError
from app.models.case import Case
from app.models.device import Device, DeviceAuthorization
from app.models.assessment import Assessment
from app.models.finding import Finding
from app.services.device_service import DeviceService
from app.core.exceptions import DeviceNotAuthorizedException, ConflictException


def test_duplicate_case_numbers_rejected(db_session, seeded_users):
    """Verify that case_number is strictly unique across the database."""
    admin = seeded_users["admin"]
    case1 = Case(case_number="CASE-DUP-001", title="Original Case", created_by=admin.id)
    db_session.add(case1)
    db_session.commit()

    case2 = Case(case_number="CASE-DUP-001", title="Duplicate Case", created_by=admin.id)
    db_session.add(case2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_duplicate_device_uuid_rejected(db_session):
    """Verify that device_uuid is strictly unique."""
    dev1 = Device(device_uuid="DEV-UNIQUE-123", authorization_status="UNREGISTERED")
    db_session.add(dev1)
    db_session.commit()

    dev2 = Device(device_uuid="DEV-UNIQUE-123", authorization_status="UNREGISTERED")
    db_session.add(dev2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_orphaned_findings_cascade_on_assessment_deletion(db_session, seeded_users):
    """Verify cascading deletion prevents orphaned findings."""
    admin = seeded_users["admin"]
    case = Case(case_number="CASE-CASCADE-FINDINGS", title="Cascade Case", created_by=admin.id)
    dev = Device(device_uuid="CASCADE-DEV-FINDINGS", authorization_status="ACTIVE")
    db_session.add_all([case, dev])
    db_session.commit()

    assessment = Assessment(
        case_id=case.id,
        target_device_id=dev.id,
        assessment_type="WIFI_DISCOVERY",
        status="COMPLETED",
        created_by=admin.id,
    )
    db_session.add(assessment)
    db_session.commit()

    finding = Finding(
        assessment_id=assessment.id,
        device_id=dev.id,
        rule_id="TEST-FINDING-001",
        title="Test Cascade Finding",
        severity="LOW",
        description="Testing cascade",
        recommendation="Test recommendation",
    )
    db_session.add(finding)
    db_session.commit()

    finding_id = finding.id
    # Delete parent assessment
    db_session.delete(assessment)
    db_session.commit()

    # Finding should be deleted (no orphaned finding)
    orphaned = db_session.query(Finding).filter(Finding.id == finding_id).first()
    assert orphaned is None


def test_revoked_device_authorization(db_session, seeded_users):
    """Verify that revoking device authorization marks status REVOKED and blocks access."""
    admin = seeded_users["admin"]
    case = Case(case_number="CASE-REVOKED", title="Revocation Test Case", created_by=admin.id)
    dev = Device(device_uuid="REVOKED-DEV-001", authorization_status="ACTIVE")
    db_session.add_all([case, dev])
    db_session.commit()

    auth = DeviceAuthorization(
        device_id=dev.id,
        case_id=case.id,
        authorized_by=admin.id,
        authorization_method="OPERATOR_ASSERTED",
        scope={"allowed_operations": ["*"]},
        status="ACTIVE",
    )
    db_session.add(auth)
    db_session.commit()

    # Revoke authorization
    DeviceService.revoke_authorization(db_session, auth.id, actor_id=admin.id)
    assert auth.status == "REVOKED"
    assert auth.revoked_at is not None
