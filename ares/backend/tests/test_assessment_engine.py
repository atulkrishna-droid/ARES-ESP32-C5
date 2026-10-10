"""Tests for the Deterministic Assessment and Rules Engine."""
import pytest
from app.android.agent_protocol import AndroidAgentProtocol
from app.assessment.engine import AssessmentEngine
from app.core.exceptions import DeviceNotAuthorizedException
from app.models.case import Case
from app.models.device import Device, DeviceAuthorization
from app.models.assessment import Assessment
from app.models.wifi_network import WifiNetwork
from app.schemas.android import AndroidDeviceSyncRequest, ApplicationSyncItem, ApplicationPermissionItem


def test_assessment_fails_if_device_unauthorized(db_session, seeded_users):
    admin = seeded_users["admin"]
    case = Case(case_number="CASE-2026-UNAUTH", title="Case Unauth", created_by=admin.id)
    dev = Device(device_uuid="UNAUTH-DEV", authorization_status="UNREGISTERED", operational_status="OFFLINE")
    db_session.add_all([case, dev])
    db_session.commit()

    assess = Assessment(
        case_id=case.id,
        target_device_id=dev.id,
        assessment_type="DEVICE_SECURITY",
        status="CREATED",
        created_by=admin.id,
    )
    db_session.add(assess)
    db_session.commit()

    with pytest.raises(DeviceNotAuthorizedException):
        AssessmentEngine.start_assessment(db_session, assess.id, actor_id=admin.id)


def test_assessment_evaluates_deterministic_rules(db_session, seeded_users):
    admin = seeded_users["admin"]

    # 1. Prepare Case and Authorized Device
    case = Case(case_number="CASE-2026-EVAL", title="Eval Case", created_by=admin.id)
    dev = Device(device_uuid="AUTH-ANDROID-DEV", authorization_status="ACTIVE", operational_status="READY")
    db_session.add_all([case, dev])
    db_session.commit()

    dev_auth = DeviceAuthorization(
        device_id=dev.id,
        case_id=case.id,
        authorized_by=admin.id,
        status="ACTIVE",
    )
    db_session.add(dev_auth)
    db_session.commit()

    # 2. Sync Android inventory with deliberate security indicators
    sync_data = AndroidDeviceSyncRequest(
        android_version="14",
        sdk_version=34,
        manufacturer="Google",
        model="Pixel 8",
        usb_debugging_status=True,  # Triggers ANDROID-DEBUG-001
        applications=[
            ApplicationSyncItem(
                package_name="com.test.debugapp",
                app_name="Debuggable App",
                debuggable=True,    # Triggers APP-DEBUG-001
                permissions=[
                    ApplicationPermissionItem(
                        permission_name="android.permission.CAMERA",
                        protection_level="dangerous",
                        granted=True,  # Triggers APP-PERM-001
                    )
                ],
            )
        ],
    )
    AndroidAgentProtocol.sync_device_inventory(db_session, dev.id, sync_data, actor_id=admin.id)

    # 3. Create Assessment
    assess = Assessment(
        case_id=case.id,
        target_device_id=dev.id,
        assessment_type="MOBILE_SECURITY",
        status="CREATED",
        scope_json={"allowed_operations": ["*"]},
        created_by=admin.id,
    )
    db_session.add(assess)
    db_session.commit()

    # 4. Add Insecure Wi-Fi observation
    wifi = WifiNetwork(
        assessment_id=assess.id,
        ssid="OPEN-INSECURE-AP",
        bssid_hash="abc123hash",
        channel=6,
        frequency=2437,
        band="2.4GHz",
        rssi=-50,
        security_type="OPEN",  # Triggers WIFI-SEC-001
    )
    db_session.add(wifi)
    db_session.commit()

    # 5. Start and Evaluate
    AssessmentEngine.start_assessment(db_session, assess.id, actor_id=admin.id)
    findings = AssessmentEngine.run_evaluation(db_session, assess.id, actor_id=admin.id)

    # Verify expected deterministic findings were raised
    rule_ids = {f.rule_id for f in findings}
    assert "ANDROID-DEBUG-001" in rule_ids
    assert "APP-DEBUG-001" in rule_ids
    assert "APP-PERM-001" in rule_ids
    assert "WIFI-SEC-001" in rule_ids
    assert assess.status == "COMPLETED"
