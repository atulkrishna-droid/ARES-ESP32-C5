"""Wi-Fi Network Observation model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WifiNetwork(Base):
    __tablename__ = "wifi_networks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)

    ssid = Column(String(100), nullable=True, index=True)
    bssid_hash = Column(String(64), nullable=False, index=True)  # SHA-256 of MAC address for privacy
    channel = Column(Integer, nullable=False)
    frequency = Column(Integer, nullable=False)                   # MHz
    band = Column(String(20), nullable=False)                     # 2.4GHz, 5GHz, 6GHz
    rssi = Column(Integer, nullable=False)                        # dBm
    security_type = Column(String(50), nullable=False)            # OPEN, WEP, WPA-PSK, WPA2-PSK, WPA3-SAE, WPA2/WPA3
    vendor = Column(String(100), nullable=True)

    first_seen = Column(DateTime, default=utcnow, nullable=False)
    last_seen = Column(DateTime, default=utcnow, nullable=False)

    assessment = relationship("Assessment", back_populates="wifi_observations")
