"""Security Audit Tests: Case-Scope Security & Cross-Case Isolation (Section 7)."""
import pytest
from datetime import datetime, timedelta, timezone
from app.assessment.engine import AssessmentEngine
from app.core.exceptions import (
    DeviceNotAuthorizedException,
    ResourceNotFoundException,
    ScopeViolationException,
)
from app.models.case import Case
from app.models.device import Device, DeviceAuthorization
from app.models.esp32_device import ESP32Device
from app.models.assessment import Assessment
from app.services.device_service import DeviceService


def test_cross_case_device_authorization_rejection(db_session, seeded_users):
    """Verify that a device authorized for Case A CANNOT be used in Case B."""
    admin = seeded_users["admin"]

    # 1. Create Case A and Case B
    case_a = Case(case_number="CASE-SCOPE-A", title="Authorized Target Case", created_by=admin.id)
    case_b = Case(case_number="CASE-SCOPE-B", title="Unauthorized Foreign Case", created_by=admin.id)
    
    # 2. Create Device A
    device_a = Device(
        device_uuid="TARGET-DEV-A",
        authorization_status="ACTIVE",
        operational_status="READY",
    )
    db_session.add_all([case_a, case_b, device_a])
    db_session.commit()

    # 3. Authorize Device A specifically for Case A
    auth_a = DeviceAuthorization(
        device_id=device_a.id,
        case_id=case_a.id,
        authorized_by=admin.id,
        authorization_method="OPERATOR_ASSERTED",
        scope={"allowed_operations": ["*"]},
        status="ACTIVE",
    )
    db_session.add(auth_a)
    db_session.commit()

    # 4. Attempt to run assessment on Case B targeting Device A -> Must be REJECTED!
    illegal_assessment = Assessment(
        case_id=case_b.id,
        target_device_id=device_a.id,
        assessment_type="WIFI_DISCOVERY",
        status="CREATED",
        scope_json={"allowed_operations": ["*"]},
        created_by=admin.id,
    )
    db_session.add(illegal_assessment)
    db_session.commit()

    with pytest.raises(DeviceNotAuthorizedException) as exc_info:
        AssessmentEngine.start_assessment(db_session, illegal_assessment.id, actor_id=admin.id)
    
    assert "does not have an active authorization for case" in str(exc_info.value).lower()
    assert illegal_assessment.status == "CREATED"


def test_scope_operation_whitelist_enforcement(client, db_session, seeded_users, auth_headers):
    """Verify that operations outside the whitelisted scope (e.g. WIFI_SCAN when only DEVICE_INVENTORY is allowed) are rejected."""
    admin = seeded_users["admin"]
    admin_headers = auth_headers["admin"]

    case = Case(case_number="CASE-INV-ONLY", title="Inventory Only Scope Case", created_by=admin.id)
    device = Device(
        device_uuid="SCOPE-LIMITED-DEV",
        authorization_status="ACTIVE",
        operational_status="READY",
    )
    db_session.add_all([case, device])
    db_session.commit()

    esp_dev = ESP32Device(
        device_id=device.id,
        chip="ESP32-C5",
        board_name="ESP32-C5-DevKitC-1",
    )
    db_session.add(esp_dev)
    db_session.commit()

    # Authorize with limited operations: DEVICE_INVENTORY only
    auth = DeviceAuthorization(
        device_id=device.id,
        case_id=case.id,
        authorized_by=admin.id,
        authorization_method="OPERATOR_ASSERTED",
        scope={"allowed_operations": ["DEVICE_INVENTORY"]},
        status="ACTIVE",
    )
    db_session.add(auth)
    db_session.commit()

    # Create assessment with restricted scope
    assessment = Assessment(
        case_id=case.id,
        target_device_id=device.id,
        assessment_type="DEVICE_SECURITY",
        status="RUNNING",
        scope_json={"allowed_operations": ["DEVICE_INVENTORY"]},
        created_by=admin.id,
    )
    db_session.add(assessment)
    db_session.commit()

    # Attempt WIFI_SCAN operation -> Must be rejected with 403 Forbidden!
    resp = client.post(
        f"/api/v1/esp32/{device.id}/wifi/scan?assessment_id={assessment.id}&dwell_time_ms=100",
        headers=admin_headers,
    )
    assert resp.status_code == 403
    assert "not authorized" in resp.json()["detail"].lower() or "scope" in resp.json()["detail"].lower()


def test_expired_authorization_rejection(db_session, seeded_users):
    """Verify that an expired device authorization fails immediately."""
    admin = seeded_users["admin"]
    case = Case(case_number="CASE-EXPIRED-AUTH", title="Expired Case", created_by=admin.id)
    device = Device(
        device_uuid="EXPIRED-DEV-001",
        authorization_status="ACTIVE",
        operational_status="READY",
    )
    db_session.add_all([case, device])
    db_session.commit()

    # Expired authorization (yesterday)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    auth = DeviceAuthorization(
        device_id=device.id,
        case_id=case.id,
        authorized_by=admin.id,
        authorization_method="OPERATOR_ASSERTED",
        scope={"allowed_operations": ["*"]},
        status="ACTIVE",
        expires_at=yesterday,
    )
    db_session.add(auth)
    db_session.commit()

    assessment = Assessment(
        case_id=case.id,
        target_device_id=device.id,
        assessment_type="WIFI_DISCOVERY",
        status="CREATED",
        created_by=admin.id,
    )
    db_session.add(assessment)
    db_session.commit()

    with pytest.raises(DeviceNotAuthorizedException) as exc_info:
        AssessmentEngine.start_assessment(db_session, assessment.id, actor_id=admin.id)
    
    assert "expired" in str(exc_info.value).lower()
