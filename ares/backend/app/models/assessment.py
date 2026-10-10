"""Assessment orchestration model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import relationship

from app.core.constants import AssessmentStatus, AssessmentType
from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    target_device_id = Column(String(36), ForeignKey("devices.id"), nullable=False, index=True)
    assessment_type = Column(String(50), default=AssessmentType.DEVICE_SECURITY.value, nullable=False, index=True)
    status = Column(String(50), default=AssessmentStatus.CREATED.value, nullable=False, index=True)
    scope_json = Column(JSON, default=dict, nullable=False)  # {device_ids: [], network_ids: [], allowed_operations: [], expires_at: ...}

    created_by = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    case = relationship("Case", back_populates="assessments")
    target_device = relationship("Device", foreign_keys=[target_device_id])
    creator = relationship("User", foreign_keys=[created_by])

    findings = relationship("Finding", back_populates="assessment", cascade="all, delete-orphan")
    wifi_observations = relationship("WifiNetwork", back_populates="assessment", cascade="all, delete-orphan")
    ble_observations = relationship("BleDevice", back_populates="assessment", cascade="all, delete-orphan")
    evidence_records = relationship("Evidence", back_populates="assessment", cascade="all, delete-orphan")
