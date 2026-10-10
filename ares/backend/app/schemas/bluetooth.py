"""Bluetooth Schemas."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class BleScanResultIngest(BaseModel):
    device_address: str = Field(..., description="Raw device address to be hashed by server")
    name: Optional[str] = None
    rssi: int
    manufacturer_id: Optional[str] = None
    manufacturer_data_hex: Optional[str] = None
    service_uuids: List[str] = Field(default_factory=list)


class BleDeviceResponse(BaseModel):
    id: str
    assessment_id: str
    device_address_hash: str
    name: Optional[str]
    rssi: int
    manufacturer_id: Optional[str]
    service_uuids: List[str]
    first_seen: datetime
    last_seen: datetime

    class Config:
        from_attributes = True
