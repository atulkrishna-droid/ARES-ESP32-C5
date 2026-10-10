"""Bluetooth Low Energy (BLE) Device Observation model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BleDevice(Base):
    __tablename__ = "ble_devices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)

    device_address_hash = Column(String(64), nullable=False, index=True)
    name = Column(String(100), nullable=True)
    rssi = Column(Integer, nullable=False)
    manufacturer_id = Column(String(50), nullable=True)
    manufacturer_data_hash = Column(String(64), nullable=True)
    service_uuids = Column(JSON, default=list, nullable=False)

    first_seen = Column(DateTime, default=utcnow, nullable=False)
    last_seen = Column(DateTime, default=utcnow, nullable=False)

    assessment = relationship("Assessment", back_populates="ble_observations")
