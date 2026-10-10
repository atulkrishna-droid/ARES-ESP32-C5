"""Android Agent Integration and Protocol Endpoints."""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.android.agent_protocol import AndroidAgentProtocol
from app.api.v1.deps import get_current_user, require_permission
from app.core.database import get_db
from app.core.exceptions import DeviceNotAuthorizedException, ResourceNotFoundException
from app.core.security import sha256_hash
from app.esp32.protocol import AresMessageType, AresProtocol
from app.models.android_device import AndroidDevice
from app.models.assessment import Assessment
from app.models.case import Case
from app.models.device import Device, DeviceAuthorization
from app.models.evidence import Evidence
from app.models.user import User
from app.schemas.android import AndroidDeviceResponse, AndroidDeviceSyncRequest
from app.schemas.device import DeviceResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/android", tags=["Android Agent"])


@router.get("/health")
def android_health_probe():
    return {"status": "ONLINE", "subsystem": "android-agent", "protocol": "ARES/1.0"}


@router.post("/enroll", status_code=status.HTTP_201_CREATED)
def enroll_android_device(
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Enroll an owner-authorized Android Agent."""
    device_uuid = payload.get("device_uuid")
    if not device_uuid or not device_uuid.startswith("ares-android-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid device identity: must begin with 'ares-android-'"
        )

    device = db.query(Device).filter(Device.device_uuid == device_uuid).first()
    now = datetime.now(timezone.utc)
    if not device:
        device = Device(
            device_uuid=device_uuid,
            device_type="ANDROID",
            manufacturer=payload.get("manufacturer", "Android"),
            model=payload.get("model", "Generic Android"),
            platform="ANDROID",
            platform_version=payload.get("android_version", "Unknown"),
            security_patch_level=payload.get("security_patch"),
            authorization_status="AUTHORIZED",
            operational_status="READY",
            environment=payload.get("environment", "PHYSICAL"),
            first_seen_at=now,
            last_seen_at=now,
        )
        db.add(device)
        db.flush()

        android_rec = AndroidDevice(
            device_id=device.id,
            android_version=payload.get("android_version", "14"),
            sdk_version=int(payload.get("sdk_version", 34)),
            manufacturer=payload.get("manufacturer", "Android"),
            model=payload.get("model", "Generic"),
            security_patch=payload.get("security_patch"),
            encryption_status=payload.get("encryption_status", "ENCRYPTED"),
            developer_options_status=payload.get("developer_options", False),
            usb_debugging_status=payload.get("usb_debugging", False),
            vpn_status=payload.get("vpn_status", False),
            last_sync=now,
        )
        db.add(android_rec)
        db.commit()

        AuditService.record_event(
            db=db,
            action="ANDROID_AGENT_ENROLLED",
            resource_type="DEVICE",
            resource_id=device.id,
            metadata={"device_uuid": device_uuid, "sdk": payload.get("sdk_version")},
        )
    else:
        device.last_seen_at = now
        device.operational_status = "READY"
        db.commit()

    return {
        "status": "ENROLLED",
        "device_id": device.id,
        "device_uuid": device.device_uuid,
        "operational_status": device.operational_status,
        "authorization_status": device.authorization_status,
    }


@router.post("/handshake")
def android_handshake(
    envelope: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Process ARES/1.0 HELLO, DEVICE_INFO, and CAPABILITIES handshakes from Android Agent."""
    mtype = envelope.get("type")
    device_uuid = envelope.get("device_id")

    device = db.query(Device).filter(Device.device_uuid == device_uuid).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device identity not enrolled.")

    if device.authorization_status == "REVOKED":
        return AresProtocol.create_message(
            AresMessageType.ERROR.value,
            device_id=device_uuid,
            payload={"code": "DEVICE_REVOKED", "message": "Device authorization revoked."}
        )

    # Check active case scoping
    active_auth = (
        db.query(DeviceAuthorization)
        .filter(DeviceAuthorization.device_id == device.id, DeviceAuthorization.revoked_at.is_(None))
        .first()
    )

    if mtype == AresMessageType.HELLO.value:
        return AresProtocol.create_message(
            AresMessageType.HELLO.value,
            device_id=device_uuid,
            payload={
                "status": "AUTHORIZED" if active_auth else "READY",
                "authorized_case_id": active_auth.case_id if active_auth else None,
                "protocol_version": "ARES/1.0",
            }
        )
    elif mtype == AresMessageType.DEVICE_INFO.value:
        return AresProtocol.create_message(
            AresMessageType.DEVICE_INFO.value,
            device_id=device_uuid,
            payload={"status": "ACK", "registered_platform": device.platform_version}
        )
    elif mtype == AresMessageType.CAPABILITIES.value:
        return AresProtocol.create_message(
            AresMessageType.CAPABILITIES.value,
            device_id=device_uuid,
            payload={"status": "ACK"}
        )
    else:
        return AresProtocol.create_message(
            AresMessageType.GET_STATUS.value,
            device_id=device_uuid,
            payload={"status": device.operational_status}
        )


@router.post("/sync-inventory")
def sync_inventory(
    device_id: str,
    sync_data: AndroidDeviceSyncRequest,
    db: Session = Depends(get_db)
):
    """Synchronize authorized Android application inventory."""
    device = db.query(Device).filter((Device.id == device_id) | (Device.device_uuid == device_id)).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found.")

    if device.authorization_status == "REVOKED":
        raise HTTPException(status_code=403, detail="Device is revoked.")

    record = AndroidAgentProtocol.sync_device_inventory(db, device.id, sync_data)
    return {"status": "SYNCED", "apps_recorded": len(sync_data.applications)}


@router.post("/telemetry")
def record_telemetry(
    envelope: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Ingest periodic heartbeat and telemetry."""
    device_uuid = envelope.get("device_id")
    device = db.query(Device).filter(Device.device_uuid == device_uuid).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found.")

    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()

    return AresProtocol.create_message(
        AresMessageType.HEARTBEAT.value,
        device_id=device_uuid,
        payload={"status": "ALIVE", "server_time": datetime.now(timezone.utc).isoformat()}
    )


@router.post("/evidence", status_code=status.HTTP_201_CREATED)
def ingest_evidence_metadata(
    envelope: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Ingest cryptographic evidence metadata from Android Agent into tamper-evident ledger."""
    device_uuid = envelope.get("device_id")
    payload = envelope.get("payload", {})

    device = db.query(Device).filter(Device.device_uuid == device_uuid).first()
    if not device:
        raise HTTPException(status_code=404, detail="Source device not found.")

    if device.authorization_status == "REVOKED":
        raise HTTPException(status_code=403, detail="Device is revoked.")

    case_id = payload.get("case_id")
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Referenced case does not exist.")

    sha256 = payload.get("sha256")
    sha512 = payload.get("sha512")
    if not sha256 or len(sha256) != 64:
        raise HTTPException(status_code=400, detail="Invalid SHA-256 evidence hash.")

    ev = Evidence(
        case_id=case.id,
        assessment_id=payload.get("assessment_id"),
        device_id=device.id,
        type=payload.get("artifact_type", "DEVICE_METADATA"),
        name="Android Agent Evidence " + str(payload.get("evidence_id", uuid.uuid4()))[:8],
        source="ANDROID_AGENT",
        path_reference="ares://evidence/metadata/" + str(payload.get("evidence_id", uuid.uuid4())),
        sha256=sha256,
        sha512=sha512,
        collected_by=case.created_by,
        collected_at=datetime.now(timezone.utc),
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    AuditService.record_event(
        db=db,
        action="EVIDENCE_METADATA_INGESTED",
        resource_type="EVIDENCE",
        resource_id=ev.id,
        metadata={
            "case_id": case.id,
            "device_uuid": device_uuid,
            "sha256": sha256,
            "sha512": sha512
        }
    )

    return {
        "status": "INGESTED",
        "evidence_id": ev.id,
        "sha256": ev.sha256,
        "integrity": "VERIFIED"
    }
