"""Integration Tests for ARES Android Agent Backend Communication."""
import hashlib
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.device import Device, DeviceAuthorization
from app.models.evidence import Evidence
from app.models.user import User


def test_android_health_probe(client: TestClient):
    resp = client.get("/api/v1/android/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ONLINE"
    assert data["subsystem"] == "android-agent"
    assert data["protocol"] == "ARES/1.0"


def test_android_device_enrollment(client: TestClient, db_session: Session):
    device_uuid = f"ares-android-{uuid.uuid4().hex[:8]}"
    payload = {
        "device_uuid": device_uuid,
        "manufacturer": "Google",
        "model": "Pixel 8 Pro",
        "android_version": "14",
        "sdk_version": 34,
        "security_patch": "2026-08-01",
        "environment": "EMULATOR",
        "developer_options": False,
        "usb_debugging": False,
    }

    resp = client.post("/api/v1/android/enroll", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "ENROLLED"
    assert data["device_uuid"] == device_uuid
    assert data["operational_status"] == "READY"

    # Reject invalid device prefix
    invalid_resp = client.post("/api/v1/android/enroll", json={"device_uuid": "invalid-prefix-1234"})
    assert invalid_resp.status_code == 400


def test_android_protocol_handshake_flow(client: TestClient, db_session: Session):
    # Setup test user and case
    user = User(
        username=f"op_{uuid.uuid4().hex[:6]}",
        email=f"op_{uuid.uuid4().hex[:6]}@ares.sec",
        password_hash="dummy_hash",
        display_name="Test Operator",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    case = Case(
        case_number=f"CASE-AND-{uuid.uuid4().hex[:6]}",
        title="Android Posture Audit",
        created_by=user.id,
    )
    db_session.add(case)
    db_session.commit()

    device_uuid = f"ares-android-{uuid.uuid4().hex[:8]}"
    client.post("/api/v1/android/enroll", json={
        "device_uuid": device_uuid,
        "android_version": "14",
        "sdk_version": 34,
    })

    dev = db_session.query(Device).filter(Device.device_uuid == device_uuid).first()
    assert dev is not None

    # Authorize device for case
    auth = DeviceAuthorization(
        device_id=dev.id,
        case_id=case.id,
        authorized_by=user.id,
        scope={"allowed_operations": ["SECURITY_POSTURE", "APPLICATION_INVENTORY"]},
    )
    db_session.add(auth)
    db_session.commit()

    # 1. HELLO handshake
    hello_frame = {
        "protocol": "ARES/1.0",
        "message_id": str(uuid.uuid4()),
        "device_id": device_uuid,
        "timestamp": "2026-09-27T14:30:00Z",
        "type": "HELLO",
        "sequence": 1,
        "payload": {"protocol_version": "ARES/1.0"},
        "signature": "UNSIGNED",
    }
    resp = client.post("/api/v1/android/handshake", json=hello_frame)
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "HELLO"
    assert data["payload"]["status"] == "AUTHORIZED"
    assert data["payload"]["authorized_case_id"] == case.id

    # 2. DEVICE_INFO query
    info_frame = {
        "protocol": "ARES/1.0",
        "message_id": str(uuid.uuid4()),
        "device_id": device_uuid,
        "timestamp": "2026-09-27T14:30:01Z",
        "type": "DEVICE_INFO",
        "sequence": 2,
        "payload": {},
        "signature": "UNSIGNED",
    }
    resp_info = client.post("/api/v1/android/handshake", json=info_frame)
    assert resp_info.status_code == 200
    assert resp_info.json()["payload"]["status"] == "ACK"


def test_android_inventory_sync_and_evidence_ingestion(client: TestClient, db_session: Session):
    user = User(
        username=f"op_{uuid.uuid4().hex[:6]}",
        email=f"op_{uuid.uuid4().hex[:6]}@ares.sec",
        password_hash="dummy_hash",
        display_name="Test Operator",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    case = Case(
        case_number=f"CASE-EV-{uuid.uuid4().hex[:6]}",
        title="Evidence Test Case",
        created_by=user.id,
    )
    db_session.add(case)
    db_session.commit()

    device_uuid = f"ares-android-{uuid.uuid4().hex[:8]}"
    client.post("/api/v1/android/enroll", json={
        "device_uuid": device_uuid,
        "android_version": "14",
        "sdk_version": 34,
    })

    # Synchronize application inventory
    sync_payload = {
        "android_version": "14",
        "sdk_version": 34,
        "manufacturer": "Google",
        "model": "Pixel 8",
        "security_patch": "2026-08-01",
        "applications": [
            {
                "package_name": "org.ares.agent",
                "app_name": "ARES Agent",
                "version_name": "1.0.0",
                "version_code": 1,
                "target_sdk": 34,
                "min_sdk": 26,
                "debuggable": False,
                "system_app": False,
                "permissions": [
                    {"permission_name": "android.permission.INTERNET", "protection_level": "normal", "granted": True}
                ],
            },
            {
                "package_name": "com.vulnerable.debug",
                "app_name": "Vulnerable App",
                "version_name": "0.1",
                "version_code": 10,
                "target_sdk": 34,
                "min_sdk": 24,
                "debuggable": True,
                "system_app": False,
                "permissions": [
                    {"permission_name": "android.permission.CAMERA", "protection_level": "dangerous", "granted": True}
                ],
            },
        ],
    }
    sync_resp = client.post(f"/api/v1/android/sync-inventory?device_id={device_uuid}", json=sync_payload)
    assert sync_resp.status_code == 200
    assert sync_resp.json()["apps_recorded"] == 2

    # Ingest Evidence Metadata
    raw_data = "TEST_EVIDENCE_PAYLOAD_CANONICAL"
    sha256 = hashlib.sha256(raw_data.encode("utf-8")).hexdigest()
    sha512 = hashlib.sha512(raw_data.encode("utf-8")).hexdigest()

    evidence_frame = {
        "protocol": "ARES/1.0",
        "message_id": str(uuid.uuid4()),
        "device_id": device_uuid,
        "timestamp": "2026-09-27T14:35:00Z",
        "type": "EVIDENCE_METADATA",
        "sequence": 3,
        "payload": {
            "evidence_id": str(uuid.uuid4()),
            "case_id": case.id,
            "artifact_type": "SECURITY_POSTURE_METADATA",
            "sha256": sha256,
            "sha512": sha512,
            "acquisition_metadata": {"apps_scanned": "2", "sdk": "34"},
        },
        "signature": "UNSIGNED",
    }
    ev_resp = client.post("/api/v1/android/evidence", json=evidence_frame)
    assert ev_resp.status_code == 201
    ev_data = ev_resp.json()
    assert ev_data["status"] == "INGESTED"
    assert ev_data["sha256"] == sha256


def test_revocation_lockdown_enforcement(client: TestClient, db_session: Session):
    device_uuid = f"ares-android-{uuid.uuid4().hex[:8]}"
    client.post("/api/v1/android/enroll", json={"device_uuid": device_uuid})

    dev = db_session.query(Device).filter(Device.device_uuid == device_uuid).first()
    assert dev is not None

    # Revoke device
    dev.authorization_status = "REVOKED"
    db_session.commit()

    # Handshake must return DEVICE_REVOKED error frame
    hello_frame = {
        "protocol": "ARES/1.0",
        "message_id": str(uuid.uuid4()),
        "device_id": device_uuid,
        "timestamp": "2026-09-27T14:40:00Z",
        "type": "HELLO",
        "sequence": 1,
        "payload": {},
        "signature": "UNSIGNED",
    }
    resp = client.post("/api/v1/android/handshake", json=hello_frame)
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "ERROR"
    assert data["payload"]["code"] == "DEVICE_REVOKED"

    # Ingesting evidence must be forbidden
    ev_frame = {
        "protocol": "ARES/1.0",
        "message_id": str(uuid.uuid4()),
        "device_id": device_uuid,
        "timestamp": "2026-09-27T14:40:05Z",
        "type": "EVIDENCE_METADATA",
        "sequence": 2,
        "payload": {"sha256": "a" * 64, "case_id": str(uuid.uuid4())},
        "signature": "UNSIGNED",
    }
    ev_resp = client.post("/api/v1/android/evidence", json=ev_frame)
    assert ev_resp.status_code == 403
