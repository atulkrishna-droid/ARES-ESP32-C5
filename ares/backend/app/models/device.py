"""Base Device and Device Authorization models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import relationship

from app.core.constants import (
    DeviceAuthorizationStatus,
    DeviceOperationalStatus,
    DeviceType,
    PlatformType,
)
from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Device(Base):
    __tablename__ = "devices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_uuid = Column(String(64), unique=True, nullable=False, index=True)
    device_type = Column(String(50), default=DeviceType.ESP32.value, nullable=False, index=True)
    manufacturer = Column(String(100), default="Generic", nullable=False)
    model = Column(String(100), default="Generic Device", nullable=False)
    serial_number_hash = Column(String(64), nullable=True)
    platform = Column(String(50), default=PlatformType.ESP_IDF.value, nullable=False)
    platform_version = Column(String(50), nullable=True)
    security_patch_level = Column(String(50), nullable=True)
    owner_label = Column(String(100), nullable=True)
    authorization_status = Column(
        String(50), default=DeviceAuthorizationStatus.UNREGISTERED.value, nullable=False, index=True
    )
    operational_status = Column(
        String(50), default=DeviceOperationalStatus.OFFLINE.value, nullable=False, index=True
    )
    environment = Column(String(30), default="PHYSICAL", nullable=False)  # PHYSICAL vs SIMULATOR
    first_seen_at = Column(DateTime, default=utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=utcnow, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    authorizations = relationship("DeviceAuthorization", back_populates="device", cascade="all, delete-orphan")
    modules = relationship("DeviceModule", cascade="all, delete-orphan")
    esp32_details = relationship("ESP32Device", back_populates="device", uselist=False, cascade="all, delete-orphan")
    android_details = relationship("AndroidDevice", back_populates="device", uselist=False, cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="device", cascade="all, delete-orphan")

    def is_authorized(self) -> bool:
        return self.authorization_status == DeviceAuthorizationStatus.ACTIVE.value


class DeviceAuthorization(Base):
    __tablename__ = "device_authorizations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    authorized_by = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    authorization_method = Column(String(50), default="OPERATOR_ASSERTED", nullable=False)
    scope = Column(JSON, default=dict, nullable=False)
    status = Column(String(50), default=DeviceAuthorizationStatus.ACTIVE.value, nullable=False, index=True)
    public_key = Column(String(512), nullable=True)
    fingerprint = Column(String(64), nullable=True)
    issued_at = Column(DateTime, default=utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    device = relationship("Device", back_populates="authorizations")
    case = relationship("Case", back_populates="authorizations")
    authorizer = relationship("User", foreign_keys=[authorized_by])
