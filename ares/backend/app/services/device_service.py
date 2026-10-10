"""Device Management and Authorization Lifecycle Service."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.constants import (
    DeviceAuthorizationStatus,
    DeviceOperationalStatus,
    DeviceType,
    PlatformType,
)
from app.core.exceptions import (
    DeviceBusyException,
    DeviceNotAuthorizedException,
    HardwareIncompatibleException,
    ResourceNotFoundException,
)
from app.models.case import Case
from app.models.device import Device, DeviceAuthorization
from app.models.esp32_device import ESP32Device
from app.models.hardware_profile import HardwareProfile
from app.schemas.device import DeviceAuthorizeRequest, DeviceEnrollRequest
from app.services.audit_service import AuditService


class DeviceService:
    @staticmethod
    def enroll_device(
        db: Session,
        request: Optional[DeviceEnrollRequest] = None,
        actor_id: Optional[str] = None,
        data: Optional[DeviceEnrollRequest] = None,
    ) -> Device:
        req = request or data
        if not req:
            raise ValueError("Device enrollment request is required.")
        device = db.query(Device).filter(Device.device_uuid == req.device_uuid).first()
        if not device:
            device = Device(
                device_uuid=req.device_uuid,
                device_type=req.device_type.value if hasattr(req.device_type, "value") else str(req.device_type),
                manufacturer=req.manufacturer,
                model=req.model,
                platform=req.platform.value if hasattr(req.platform, "value") else str(req.platform),
                platform_version=req.platform_version,
                owner_label=req.owner_label,
                environment=req.environment,
                authorization_status=DeviceAuthorizationStatus.ENROLLMENT_REQUESTED.value,
                operational_status=DeviceOperationalStatus.DISCOVERED.value,
            )
            db.add(device)
            db.flush()

            # If ESP32, attach ESP32 specialization
            dtype = req.device_type.value if hasattr(req.device_type, "value") else str(req.device_type)
            if dtype == DeviceType.ESP32.value:
                # Find matching default profile
                profile = db.query(HardwareProfile).filter(HardwareProfile.board_name == req.model).first()
                esp_record = ESP32Device(
                    device_id=device.id,
                    hardware_profile_id=profile.id if profile else None,
                    chip="ESP32-C5" if "C5" in req.model else "ESP32",
                    board_name=req.model,
                    board_revision="v1.0",
                    flash_size="8MB",
                    psram_size="8MB",
                    status="DISCOVERED",
                )
                db.add(esp_record)

            db.commit()
            db.refresh(device)

            AuditService.record_event(
                db=db,
                action="DEVICE_ENROLLED",
                resource_type="DEVICE",
                resource_id=device.id,
                actor_id=actor_id,
                metadata={"device_uuid": device.device_uuid, "model": device.model},
            )
        return device

    @staticmethod
    def authorize_device(
        db: Session,
        device_id: str,
        request: Optional[DeviceAuthorizeRequest] = None,
        actor_id: str = None,
        data: Optional[DeviceAuthorizeRequest] = None,
    ) -> DeviceAuthorization:
        req = request or data
        if not req:
            raise ValueError("Device authorization request is required.")
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise ResourceNotFoundException("Device not found.")

        case = db.query(Case).filter(Case.id == req.case_id).first()
        if not case:
            raise ResourceNotFoundException("Specified assessment Case not found.")

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=req.expires_in_days or 30)

        # Deactivate any previous authorizations for this device
        prev_auths = db.query(DeviceAuthorization).filter(
            DeviceAuthorization.device_id == device_id,
            DeviceAuthorization.status == DeviceAuthorizationStatus.ACTIVE.value,
        ).all()
        for p in prev_auths:
            p.status = DeviceAuthorizationStatus.EXPIRED.value

        method = req.authorization_method.value if hasattr(req.authorization_method, "value") else str(req.authorization_method)
        auth = DeviceAuthorization(
            device_id=device.id,
            case_id=case.id,
            authorized_by=actor_id,
            authorization_method=method,
            scope=req.scope or {"allowed_operations": ["*"]},
            status=DeviceAuthorizationStatus.ACTIVE.value,
            public_key=req.public_key,
            fingerprint=req.fingerprint,
            issued_at=now,
            expires_at=expires_at,
        )

        device.authorization_status = DeviceAuthorizationStatus.ACTIVE.value
        device.operational_status = DeviceOperationalStatus.READY.value
        db.add(auth)
        db.commit()
        db.refresh(auth)

        AuditService.record_event(
            db=db,
            action="DEVICE_AUTHORIZED",
            resource_type="DEVICE",
            resource_id=device.id,
            actor_id=actor_id,
            metadata={"case_id": case.id, "authorization_id": auth.id, "scope": auth.scope},
        )
        return auth

    @staticmethod
    def revoke_device(db: Session, device_id: str, actor_id: str, reason: str = "Operator revocation") -> Device:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise ResourceNotFoundException("Device not found.")

        device.authorization_status = DeviceAuthorizationStatus.REVOKED.value
        device.operational_status = DeviceOperationalStatus.REVOKED.value

        # Revoke all active authorizations
        active_auths = db.query(DeviceAuthorization).filter(
            DeviceAuthorization.device_id == device_id,
            DeviceAuthorization.status == DeviceAuthorizationStatus.ACTIVE.value,
        ).all()
        now = datetime.now(timezone.utc)
        for a in active_auths:
            a.status = DeviceAuthorizationStatus.REVOKED.value
            a.revoked_at = now

        db.commit()
        db.refresh(device)

        AuditService.record_event(
            db=db,
            action="DEVICE_REVOKED",
            resource_type="DEVICE",
            resource_id=device.id,
            actor_id=actor_id,
            metadata={"reason": reason},
        )
        return device

    @staticmethod
    def revoke_authorization(db: Session, authorization_id: str, actor_id: str) -> DeviceAuthorization:
        auth = db.query(DeviceAuthorization).filter(DeviceAuthorization.id == authorization_id).first()
        if not auth:
            raise ResourceNotFoundException("Authorization record not found.")
        now = datetime.now(timezone.utc)
        auth.status = DeviceAuthorizationStatus.REVOKED.value
        auth.revoked_at = now
        db.commit()
        db.refresh(auth)
        AuditService.record_event(
            db=db,
            action="DEVICE_AUTHORIZATION_REVOKED",
            resource_type="DEVICE_AUTHORIZATION",
            resource_id=auth.id,
            actor_id=actor_id,
        )
        return auth

    @staticmethod
    def acquire_device_lock(db: Session, device_id: str, assessment_id: str) -> None:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise ResourceNotFoundException("Device not found.")

        if not device.is_authorized():
            raise DeviceNotAuthorizedException("Device is not in ACTIVE authorization status.")

        if device.operational_status == DeviceOperationalStatus.BUSY.value:
            raise DeviceBusyException("Device is already executing another assessment.")

        device.operational_status = DeviceOperationalStatus.BUSY.value
        db.commit()

    @staticmethod
    def release_device_lock(db: Session, device_id: str) -> None:
        device = db.query(Device).filter(Device.id == device_id).first()
        if device and device.operational_status == DeviceOperationalStatus.BUSY.value:
            device.operational_status = DeviceOperationalStatus.READY.value
            db.commit()
