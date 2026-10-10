"""Device and Authorization Schemas."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.constants import (
    AuthorizationMethod,
    DeviceAuthorizationStatus,
    DeviceOperationalStatus,
    DeviceType,
    PlatformType,
)


class DeviceEnrollRequest(BaseModel):
    device_uuid: str = Field(..., min_length=4, max_length=64)
    device_type: DeviceType = DeviceType.ESP32
    manufacturer: str = "Generic"
    model: str = "ESP32-C5-DevKitC-1"
    platform: PlatformType = PlatformType.ESP_IDF
    platform_version: Optional[str] = "v5.3"
    owner_label: Optional[str] = None
    environment: str = "PHYSICAL"
    firmware_version: Optional[str] = None
    hardware_revision: Optional[str] = None


class DeviceAuthorizeRequest(BaseModel):
    case_id: str
    authorization_method: AuthorizationMethod = AuthorizationMethod.ADMIN_APPROVAL
    scope: Dict[str, Any] = Field(default_factory=dict)
    public_key: Optional[str] = None
    fingerprint: Optional[str] = None
    expires_in_days: Optional[int] = 30


class DeviceRevokeRequest(BaseModel):
    reason: Optional[str] = "Assessment concluded or operator revocation."


class DeviceAuthorizationResponse(BaseModel):
    id: str
    device_id: str
    case_id: str
    authorized_by: str
    authorization_method: str
    scope: Dict[str, Any]
    status: str
    fingerprint: Optional[str]
    issued_at: datetime
    expires_at: Optional[datetime]
    revoked_at: Optional[datetime]

    class Config:
        from_attributes = True


class DeviceResponse(BaseModel):
    id: str
    device_uuid: str
    device_type: str
    manufacturer: str
    model: str
    platform: str
    platform_version: Optional[str]
    security_patch_level: Optional[str]
    owner_label: Optional[str]
    authorization_status: str
    operational_status: str
    environment: str
    first_seen_at: datetime
    last_seen_at: datetime
    is_authorized: bool

    class Config:
        from_attributes = True
