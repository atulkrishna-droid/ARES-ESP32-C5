"""Case management model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.core.constants import CasePriority, CaseStatus
from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_number = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(30), default=CaseStatus.OPEN.value, nullable=False, index=True)
    priority = Column(String(20), default=CasePriority.MEDIUM.value, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)

    creator = relationship("User", foreign_keys=[created_by])
    assessments = relationship("Assessment", back_populates="case", cascade="all, delete-orphan")
    evidence_items = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    authorizations = relationship("DeviceAuthorization", back_populates="case", cascade="all, delete-orphan")
