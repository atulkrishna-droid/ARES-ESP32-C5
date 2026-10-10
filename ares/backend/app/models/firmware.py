"""Firmware and Hardware Compatibility models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.constants import ReleaseChannel
from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Firmware(Base):
    __tablename__ = "firmwares"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    firmware_family = Column(String(50), default="ARES", nullable=False)  # ARES, MARAUDER, CUSTOM
    chip = Column(String(50), nullable=False, index=True)                 # ESP32-C5
    board_target = Column(String(100), nullable=False, index=True)         # ESP32-C5-DevKitC-1
    protocol_version = Column(String(30), default="ARES/1.0", nullable=False)
    build_hash = Column(String(64), nullable=False)
    release_channel = Column(String(30), default=ReleaseChannel.STABLE.value, nullable=False)
    checksum = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    compatibilities = relationship("FirmwareCompatibility", back_populates="firmware", cascade="all, delete-orphan")


class FirmwareCompatibility(Base):
    __tablename__ = "firmware_compatibilities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    firmware_id = Column(String(36), ForeignKey("firmwares.id", ondelete="CASCADE"), nullable=False, index=True)
    hardware_profile_id = Column(String(36), ForeignKey("hardware_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    minimum_revision = Column(String(30), default="v1.0", nullable=False)
    maximum_revision = Column(String(30), default="v99.9", nullable=False)
    partition_layout = Column(String(50), default="default_8MB", nullable=False)
    flash_required = Column(String(30), default="8MB", nullable=False)
    psram_required = Column(String(30), default="8MB", nullable=False)

    firmware = relationship("Firmware", back_populates="compatibilities")
    hardware_profile = relationship("HardwareProfile")
