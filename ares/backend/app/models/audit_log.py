"""Tamper-evident Audit Log model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)          # e.g., DEVICE_ENROLLED, ASSESSMENT_STARTED
    resource_type = Column(String(50), nullable=False, index=True)    # e.g., DEVICE, ASSESSMENT, EVIDENCE
    resource_id = Column(String(64), nullable=True, index=True)
    timestamp = Column(DateTime, default=utcnow, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)

    # Tamper-evident cryptographic chaining
    previous_event_hash = Column(String(64), nullable=True)
    event_hash = Column(String(64), nullable=False, index=True)

    actor = relationship("User", foreign_keys=[actor_id])

    @property
    def previous_hash(self):
        return self.previous_event_hash

    @property
    def current_hash(self):
        return self.event_hash

    @property
    def sequence_number(self):
        return self.id

    @property
    def details(self):
        return self.metadata_json

    @details.setter
    def details(self, val):
        self.metadata_json = val
