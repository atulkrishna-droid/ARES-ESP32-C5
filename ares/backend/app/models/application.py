"""Application and Application Permission models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Application(Base):
    __tablename__ = "applications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    package_name = Column(String(255), nullable=False, index=True)
    app_name = Column(String(255), nullable=False)
    version_name = Column(String(100), nullable=True)
    version_code = Column(Integer, nullable=True)
    target_sdk = Column(Integer, nullable=True)
    min_sdk = Column(Integer, nullable=True)
    debuggable = Column(Boolean, default=False, nullable=False)
    system_app = Column(Boolean, default=False, nullable=False)
    install_time = Column(DateTime, nullable=True)
    update_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    device = relationship("Device", back_populates="applications")
    permissions = relationship("ApplicationPermission", back_populates="application", cascade="all, delete-orphan")


class ApplicationPermission(Base):
    __tablename__ = "application_permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_name = Column(String(255), nullable=False, index=True)  # e.g., android.permission.CAMERA
    permission_group = Column(String(100), nullable=True)             # e.g., CAMERA, LOCATION
    protection_level = Column(String(50), default="normal", nullable=False)  # normal, dangerous, signature
    granted = Column(Boolean, default=False, nullable=False)
    assessment_result = Column(String(50), default="REVIEW_REQUIRED", nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    application = relationship("Application", back_populates="permissions")
