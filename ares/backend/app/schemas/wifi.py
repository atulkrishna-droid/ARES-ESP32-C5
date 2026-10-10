"""Wi-Fi Schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class WifiScanResultIngest(BaseModel):
    ssid: Optional[str] = "<HIDDEN>"
    bssid: str = Field(..., description="Raw BSSID or MAC address to be hashed by server")
    channel: int
    frequency: int
    band: str = "2.4GHz"  # 2.4GHz, 5GHz, 6GHz
    rssi: int
    security_type: str = "OPEN"
    vendor: Optional[str] = None


class WifiNetworkResponse(BaseModel):
    id: str
    assessment_id: str
    ssid: Optional[str]
    bssid_hash: str
    channel: int
    frequency: int
    band: str
    rssi: int
    security_type: str
    vendor: Optional[str]
    first_seen: datetime
    last_seen: datetime

    class Config:
        from_attributes = True
