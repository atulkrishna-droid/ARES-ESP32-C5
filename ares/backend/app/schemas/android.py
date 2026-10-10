"""Android Device and Mobile Assessment Schemas."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ApplicationPermissionItem(BaseModel):
    permission_name: str
    permission_group: Optional[str] = None
    protection_level: str = "normal"
    granted: bool = False


class ApplicationSyncItem(BaseModel):
    package_name: str
    app_name: str
    version_name: Optional[str] = None
    version_code: Optional[int] = None
    target_sdk: Optional[int] = None
    min_sdk: Optional[int] = None
    debuggable: bool = False
    system_app: bool = False
    permissions: List[ApplicationPermissionItem] = []


class AndroidDeviceSyncRequest(BaseModel):
    android_version: str
    sdk_version: int
    manufacturer: str
    model: str
    security_patch: Optional[str] = None
    build_fingerprint_hash: Optional[str] = None
    encryption_status: Optional[str] = "ENCRYPTED"
    developer_options_status: Optional[bool] = False
    usb_debugging_status: Optional[bool] = False
    vpn_status: Optional[bool] = False
    network_security_indicators: Dict[str, Any] = Field(default_factory=dict)
    unexposed_properties: List[str] = Field(default_factory=list)
    applications: List[ApplicationSyncItem] = Field(default_factory=list)


class ApplicationResponse(BaseModel):
    id: str
    package_name: str
    app_name: str
    version_name: Optional[str]
    version_code: Optional[int]
    target_sdk: Optional[int]
    debuggable: bool
    system_app: bool

    class Config:
        from_attributes = True


class AndroidDeviceResponse(BaseModel):
    id: str
    device_id: str
    android_version: str
    sdk_version: int
    manufacturer: str
    model: str
    security_patch: Optional[str]
    encryption_status: Optional[str]
    developer_options_status: Optional[bool]
    usb_debugging_status: Optional[bool]
    vpn_status: Optional[bool]
    last_sync: datetime

    class Config:
        from_attributes = True
