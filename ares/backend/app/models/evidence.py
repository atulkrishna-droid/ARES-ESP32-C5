"""Forensics Evidence and Chain of Custody models."""
import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.core.constants import ChainOfCustodyEventType, EvidenceType
from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True, index=True)
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True)

    type = Column(String(50), default=EvidenceType.DEVICE_METADATA.value, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source = Column(String(100), nullable=False)  # ESP32_C5, ANDROID_AGENT, LAB_SIMULATOR
    path_reference = Column(String(500), nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    sha512 = Column(String(128), nullable=True)
    size_bytes = Column(BigInteger, default=0, nullable=False)

    collected_at = Column(DateTime, default=utcnow, nullable=False)
    collected_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    case = relationship("Case", back_populates="evidence_items")
    assessment = relationship("Assessment", back_populates="evidence_records")
    device = relationship("Device")
    collector = relationship("User", foreign_keys=[collected_by])
    custody_events = relationship("ChainOfCustodyEvent", back_populates="evidence", cascade="all, delete-orphan", order_by="ChainOfCustodyEvent.timestamp")

    @property
    def sha256_hash(self) -> str:
        return self.sha256

    @property
    def sha512_hash(self) -> Optional[str]:
        return self.sha512

    @property
    def custody_entries(self):
        return self.custody_events

    @property
    def file_name(self) -> str:
        return self.name

    @property
    def storage_path(self) -> str:
        return self.path_reference


class ChainOfCustodyEvent(Base):
    __tablename__ = "chain_of_custody_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evidence_id = Column(String(36), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    event_type = Column(String(50), default=ChainOfCustodyEventType.COLLECTED.value, nullable=False)
    timestamp = Column(DateTime, default=utcnow, nullable=False, index=True)
    description = Column(String(500), nullable=False)
    previous_hash = Column(String(64), nullable=True)
    event_hash = Column(String(64), nullable=False)

    evidence = relationship("Evidence", back_populates="custody_events")
    actor = relationship("User", foreign_keys=[actor_id])

    @property
    def action(self) -> str:
        return self.event_type
