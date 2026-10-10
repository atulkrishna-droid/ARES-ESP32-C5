"""ESP32 and Hardware Profile Schemas."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ESP32PairRequest(BaseModel):
    device_uuid: str
    chip: str = "ESP32-C5"
    board_name: str = "ESP32-C5-DevKitC-1"
    board_revision: str = "v1.0"
    flash_size: str = "8MB"
    psram_size: str = "8MB"
    firmware_version: str = "1.0.0"
    protocol_version: str = "ARES/1.0"
    public_key: Optional[str] = None


class ESP32TelemetryRequest(BaseModel):
    uptime_seconds: int
    free_heap: int
    free_psram: Optional[int] = 0
    wifi_state: str = "IDLE"
    ble_state: str = "IDLE"
    sd_state: str = "NOT_INSTALLED"
    usb_state: str = "CONNECTED"
    temperature_c: Optional[float] = None
    power_source: str = "USB"
    rssi: Optional[int] = None


class ESP32CommandRequest(BaseModel):
    command: str = Field(..., description="Whitelisted ARES command")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class HardwareProfileResponse(BaseModel):
    id: str
    name: str
    chip: str
    board_name: str
    flash_size: str
    psram_size: str
    wifi_24: bool
    wifi_5: bool
    wifi6: bool
    ble: bool
    bluetooth_classic: bool
    ieee802154: bool
    zigbee: bool
    thread: bool
    usb: bool
    sd: bool
    gps: bool
    peripheral_pinouts: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class ESP32Response(BaseModel):
    id: str
    device_id: str
    chip: str
    board_name: str
    board_revision: str
    flash_size: str
    psram_size: str
    firmware_version: str
    protocol_version: str
    status: str
    last_heartbeat: datetime
    latest_telemetry: Dict[str, Any] = {}

    class Config:
        from_attributes = True
