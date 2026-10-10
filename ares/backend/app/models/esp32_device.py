"""ESP32-Specific Device specialization model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ESP32Device(Base):
    __tablename__ = "esp32_devices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), unique=True, nullable=False)
    hardware_profile_id = Column(String(36), ForeignKey("hardware_profiles.id"), nullable=True)
    firmware_id = Column(String(36), ForeignKey("firmwares.id"), nullable=True)

    chip = Column(String(50), default="ESP32-C5", nullable=False)
    board_name = Column(String(100), default="ESP32-C5-DevKitC-1", nullable=False)
    board_revision = Column(String(30), default="v1.0", nullable=False)
    flash_size = Column(String(30), default="8MB", nullable=False)
    psram_size = Column(String(30), default="8MB", nullable=False)
    mac_address_hash = Column(String(64), nullable=True)
    usb_serial = Column(String(100), nullable=True)
    firmware_version = Column(String(50), default="1.0.0", nullable=False)
    protocol_version = Column(String(30), default="ARES/1.0", nullable=False)

    status = Column(String(50), default="READY", nullable=False)
    last_heartbeat = Column(DateTime, default=utcnow, nullable=False)
    latest_telemetry = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    device = relationship("Device", back_populates="esp32_details")
    hardware_profile = relationship("HardwareProfile")
    firmware = relationship("Firmware")
