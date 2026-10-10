"""Unit and integration tests for Device enrollment and authorization boundaries."""
import pytest
from app.core.exceptions import DeviceBusyException, DeviceNotAuthorizedException
from app.models.case import Case
from app.models.device import Device
from app.schemas.device import DeviceAuthorizeRequest, DeviceEnrollRequest
from app.services.device_service import DeviceService


def test_device_enrollment_and_authorization(db_session, seeded_users):
    admin = seeded_users["admin"]

    # 1. Enroll device
    enroll_req = DeviceEnrollRequest(
        device_uuid="TEST-ESP32-001",
        device_type="ESP32",
        manufacturer="Espressif",
        model="ESP32-C5-DevKitC-1",
    )
    device = DeviceService.enroll_device(db_session, enroll_req, actor_id=admin.id)
    assert device.id is not None
    assert device.authorization_status == "ENROLLMENT_REQUESTED"
    assert device.is_authorized() is False

    # 2. Create case
    case = Case(
        case_number="CASE-2026-TEST01",
        title="Test Case",
        created_by=admin.id,
    )
    db_session.add(case)
    db_session.commit()

    # 3. Authorize device
    auth_req = DeviceAuthorizeRequest(
        case_id=case.id,
        authorization_method="ADMIN_APPROVAL",
        scope={"allowed_operations": ["WIFI_DISCOVERY"]},
    )
    auth = DeviceService.authorize_device(db_session, device.id, auth_req, actor_id=admin.id)
    assert auth.status == "ACTIVE"
    assert device.authorization_status == "ACTIVE"
    assert device.is_authorized() is True

    # 4. Device locking
    DeviceService.acquire_device_lock(db_session, device.id, "ASSESS-001")
    assert device.operational_status == "BUSY"

    # Conflicting lock attempt must fail
    with pytest.raises(DeviceBusyException):
        DeviceService.acquire_device_lock(db_session, device.id, "ASSESS-002")

    # Release lock
    DeviceService.release_device_lock(db_session, device.id)
    assert device.operational_status == "READY"

    # 5. Revocation
    DeviceService.revoke_device(db_session, device.id, actor_id=admin.id)
    assert device.authorization_status == "REVOKED"
    assert device.is_authorized() is False

    # Attempting to acquire lock on revoked device must fail
    with pytest.raises(DeviceNotAuthorizedException):
        DeviceService.acquire_device_lock(db_session, device.id, "ASSESS-003")
