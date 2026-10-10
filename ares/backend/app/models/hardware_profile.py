"""Hardware Profile, Module, Antenna, and Power models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HardwareProfile(Base):
    __tablename__ = "hardware_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False)
    chip = Column(String(50), nullable=False, index=True)  # e.g., "ESP32-C5"
    board_name = Column(String(100), nullable=False)       # e.g., "ESP32-C5-DevKitC-1"
    flash_size = Column(String(30), default="8MB", nullable=False)
    psram_size = Column(String(30), default="8MB", nullable=False)

    # Wireless Capabilities
    wifi_24 = Column(Boolean, default=True, nullable=False)
    wifi_5 = Column(Boolean, default=True, nullable=False)
    wifi6 = Column(Boolean, default=True, nullable=False)
    ble = Column(Boolean, default=True, nullable=False)
    bluetooth_classic = Column(Boolean, default=False, nullable=False)  # ESP32-C5 does not support BT Classic
    ieee802154 = Column(Boolean, default=True, nullable=False)
    zigbee = Column(Boolean, default=True, nullable=False)
    thread = Column(Boolean, default=True, nullable=False)

    # Physical / Peripheral Capabilities
    usb = Column(Boolean, default=True, nullable=False)
    sd = Column(Boolean, default=False, nullable=False)               # Optional external module on DevKitC-1
    gps = Column(Boolean, default=False, nullable=False)              # Optional external module
    external_wifi_antenna = Column(Boolean, default=False, nullable=False)
    battery = Column(Boolean, default=False, nullable=False)
    display = Column(Boolean, default=False, nullable=False)
    touchscreen = Column(Boolean, default=False, nullable=False)

    # Documented pinout mapping for external peripherals (e.g. SPI MicroSD: MISO GPIO2, MOSI GPIO7, SCK GPIO6, CS GPIO10)
    peripheral_pinouts = Column(JSON, default=dict, nullable=False)

    created_at = Column(DateTime, default=utcnow, nullable=False)


class DeviceModule(Base):
    __tablename__ = "device_modules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    module_type = Column(String(50), nullable=False)  # MICROSD, GPS, BATTERY, DISPLAY, ANTENNA, SENSOR
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    interface = Column(String(50), nullable=False)    # SPI, I2C, UART, GPIO
    status = Column(String(30), default="ATTACHED", nullable=False)
    configuration = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class AntennaProfile(Base):
    __tablename__ = "antenna_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    connector = Column(String(50), nullable=False)  # U.FL / IPEX, SMA
    frequency_min_mhz = Column(Integer, default=2400, nullable=False)
    frequency_max_mhz = Column(Integer, default=5850, nullable=False)
    gain_db = Column(Float, default=2.5, nullable=False)
    polarization = Column(String(50), default="LINEAR", nullable=False)
    antenna_type = Column(String(50), default="DUAL_BAND_OMNI", nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class PowerProfile(Base):
    __tablename__ = "power_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    power_source = Column(String(50), default="USB", nullable=False)  # USB, BATTERY, EXTERNAL
    voltage = Column(Float, default=5.0, nullable=False)
    current_limit_ma = Column(Integer, default=500, nullable=False)
    battery_level_percent = Column(Integer, nullable=True)
    is_charging = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
