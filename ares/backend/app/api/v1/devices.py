"""Device Management and Authorization Endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_permission
from app.core.database import get_db
from app.models.device import Device
from app.models.user import User
from app.schemas.device import (
    DeviceAuthorizationResponse,
    DeviceAuthorizeRequest,
    DeviceEnrollRequest,
    DeviceResponse,
    DeviceRevokeRequest,
)
from app.services.device_service import DeviceService

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("", response_model=List[DeviceResponse], dependencies=[Depends(require_permission("device.read"))])
def list_devices(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    devices = db.query(Device).offset(skip).limit(limit).all()
    return [
        DeviceResponse(
            id=d.id,
            device_uuid=d.device_uuid,
            device_type=d.device_type,
            manufacturer=d.manufacturer,
            model=d.model,
            platform=d.platform,
            platform_version=d.platform_version,
            security_patch_level=d.security_patch_level,
            owner_label=d.owner_label,
            authorization_status=d.authorization_status,
            operational_status=d.operational_status,
            environment=d.environment,
            first_seen_at=d.first_seen_at,
            last_seen_at=d.last_seen_at,
            is_authorized=d.is_authorized(),
        )
        for d in devices
    ]


@router.post("/enroll", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("device.enroll"))])
def enroll_device(request: DeviceEnrollRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d = DeviceService.enroll_device(db, request, actor_id=current_user.id)
    return DeviceResponse(
        id=d.id,
        device_uuid=d.device_uuid,
        device_type=d.device_type,
        manufacturer=d.manufacturer,
        model=d.model,
        platform=d.platform,
        platform_version=d.platform_version,
        security_patch_level=d.security_patch_level,
        owner_label=d.owner_label,
        authorization_status=d.authorization_status,
        operational_status=d.operational_status,
        environment=d.environment,
        first_seen_at=d.first_seen_at,
        last_seen_at=d.last_seen_at,
        is_authorized=d.is_authorized(),
    )


@router.get("/{device_id}", response_model=DeviceResponse, dependencies=[Depends(require_permission("device.read"))])
def get_device(device_id: str, db: Session = Depends(get_db)):
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found.")
    return DeviceResponse(
        id=d.id,
        device_uuid=d.device_uuid,
        device_type=d.device_type,
        manufacturer=d.manufacturer,
        model=d.model,
        platform=d.platform,
        platform_version=d.platform_version,
        security_patch_level=d.security_patch_level,
        owner_label=d.owner_label,
        authorization_status=d.authorization_status,
        operational_status=d.operational_status,
        environment=d.environment,
        first_seen_at=d.first_seen_at,
        last_seen_at=d.last_seen_at,
        is_authorized=d.is_authorized(),
    )


@router.post("/{device_id}/authorize", response_model=DeviceAuthorizationResponse, dependencies=[Depends(require_permission("device.authorize"))])
def authorize_device(device_id: str, request: DeviceAuthorizeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return DeviceService.authorize_device(db, device_id, request, actor_id=current_user.id)


@router.post("/{device_id}/revoke", response_model=DeviceResponse, dependencies=[Depends(require_permission("device.revoke"))])
def revoke_device(device_id: str, request: DeviceRevokeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d = DeviceService.revoke_device(db, device_id, actor_id=current_user.id, reason=request.reason or "Operator revocation")
    return DeviceResponse(
        id=d.id,
        device_uuid=d.device_uuid,
        device_type=d.device_type,
        manufacturer=d.manufacturer,
        model=d.model,
        platform=d.platform,
        platform_version=d.platform_version,
        security_patch_level=d.security_patch_level,
        owner_label=d.owner_label,
        authorization_status=d.authorization_status,
        operational_status=d.operational_status,
        environment=d.environment,
        first_seen_at=d.first_seen_at,
        last_seen_at=d.last_seen_at,
        is_authorized=d.is_authorized(),
    )
