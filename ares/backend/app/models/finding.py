"""Deterministic Security Finding model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from app.core.constants import FindingSeverity, FindingStatus
from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Finding(Base):
    __tablename__ = "findings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(String(100), nullable=False, index=True)  # e.g., ANDROID-DEBUG-001, APP-DEBUG-001
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = Column(String(36), ForeignKey("applications.id", ondelete="SET NULL"), nullable=True)

    severity = Column(String(30), default=FindingSeverity.LOW.value, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    evidence_json = Column(JSON, default=dict, nullable=False)
    recommendation = Column(Text, nullable=False)
    status = Column(String(50), default=FindingStatus.OPEN.value, nullable=False, index=True)

    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)

    assessment = relationship("Assessment", back_populates="findings")
    device = relationship("Device")
    application = relationship("Application")
