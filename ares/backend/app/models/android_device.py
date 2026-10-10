"""Android-Specific Device specialization model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AndroidDevice(Base):
    __tablename__ = "android_devices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), unique=True, nullable=False)

    android_version = Column(String(30), nullable=False)  # e.g., "14"
    sdk_version = Column(Integer, nullable=False)          # e.g., 34
    manufacturer = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    security_patch = Column(String(30), nullable=True)    # e.g., "2024-03-01"
    build_fingerprint_hash = Column(String(64), nullable=True)

    # Security indicators
    encryption_status = Column(String(50), default="ENCRYPTED", nullable=True)
    developer_options_status = Column(Boolean, default=False, nullable=True)
    usb_debugging_status = Column(Boolean, default=False, nullable=True)
    vpn_status = Column(Boolean, default=False, nullable=True)
    network_security_indicators = Column(JSON, default=dict, nullable=False)

    # Explicit tracker for unexposed platform properties
    unexposed_properties = Column(JSON, default=list, nullable=False)
    last_sync = Column(DateTime, default=utcnow, nullable=False)

    device = relationship("Device", back_populates="android_details")
