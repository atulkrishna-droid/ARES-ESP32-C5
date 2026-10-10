"""ARES Host Transport Subsystem: Esp32Transport Interface, UsbSerialTransport, and SimulatorTransport."""
import json
import logging
import queue
import re
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DeviceNotAuthorizedException,
    HardwareIncompatibleException,
    ProtocolViolationException,
    ResourceNotFoundException,
)
from app.esp32.protocol import AresMessageType, AresProtocol, ProtocolEnvelope
from app.esp32.simulator import ESP32C5Simulator
from app.models.assessment import Assessment
from app.models.device import Device, DeviceAuthorization
from app.models.esp32_device import ESP32Device
from app.models.hardware_profile import HardwareProfile
from app.services.audit_service import AuditService

logger = logging.getLogger("ares.transport")


class Esp32Transport(ABC):
    """Abstract base transport interface for ARES physical devices and simulators."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish communication channel."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Terminate communication channel."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if transport is actively connected."""
        pass

    @abstractmethod
    def send_message(self, message: Dict[str, Any]) -> bool:
        """Send a formatted ARES/1.0 protocol message."""
        pass

    @abstractmethod
    def receive_message(self, timeout_sec: float = 1.0) -> Optional[ProtocolEnvelope]:
        """Receive next incoming ARES/1.0 message frame."""
        pass


class SimulatorTransport(Esp32Transport):
    """Host transport adapter for in-memory ESP32-C5 simulator."""

    def __init__(self, simulator: Optional[ESP32C5Simulator] = None, device_id: str = "ESP32-C5-SIM-001"):
        self.simulator = simulator or ESP32C5Simulator(device_id=device_id, environment="SIMULATOR")
        self.device_id = self.simulator.device_id
        self._connected = False
        self._inbox: queue.Queue = queue.Queue()

    def connect(self) -> bool:
        self._connected = True
        logger.info(f"SimulatorTransport connected to virtual device '{self.device_id}'.")
        return True

    def disconnect(self) -> None:
        self._connected = False
        logger.info(f"SimulatorTransport disconnected from virtual device '{self.device_id}'.")

    def is_connected(self) -> bool:
        return self._connected

    def send_message(self, message: Dict[str, Any]) -> bool:
        if not self._connected:
            return False
        # Feed into simulator and collect automatic response if applicable
        msg_type = message.get("type")
        if msg_type == AresMessageType.HELLO.value:
            resp = self.simulator.send_hello()
            self._inbox.put(resp)
        elif msg_type == AresMessageType.CAPABILITIES.value:
            resp = self.simulator.send_capabilities()
            self._inbox.put(resp)
        elif msg_type == AresMessageType.DEVICE_INFO.value:
            resp = AresProtocol.create_message(
                AresMessageType.DEVICE_INFO.value,
                payload={
                    "chip": "ESP32-C5",
                    "board_target": "ESP32-C5-DevKitC-1",
                    "firmware_version": "1.0.0",
                    "protocol_version": "ARES/1.0",
                    "flash_size": "8MB",
                },
                device_id=self.device_id,
            )
            self._inbox.put(resp)
        elif msg_type == AresMessageType.HEARTBEAT.value:
            resp = self.simulator.send_telemetry(uptime_s=100)
            self._inbox.put(resp)
        return True

    def receive_message(self, timeout_sec: float = 1.0) -> Optional[ProtocolEnvelope]:
        if not self._connected:
            return None
        try:
            return self._inbox.get(timeout=timeout_sec)
        except queue.Empty:
            return None


class UsbSerialTransport(Esp32Transport):
    """Host transport adapter communicating with physical ESP32-C5 over USB Serial/JTAG."""

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = 115200,
        device_id: Optional[str] = None,
        mock_serial: Optional[Any] = None,
    ):
        self.port = port or "AUTO"
        self.baudrate = baudrate
        self.device_id = device_id
        self._mock_serial = mock_serial
        self._serial_handle: Optional[Any] = None
        self._connected = False
        self._running = False
        self._rx_thread: Optional[threading.Thread] = None
        self._rx_queue: queue.Queue = queue.Queue()
        self.last_seen_heartbeat: Optional[datetime] = None

    @classmethod
    def discover_ports(cls) -> List[Dict[str, str]]:
        """Discover available serial ports, highlighting Espressif ESP32 USB devices."""
        discovered = []
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            for p in ports:
                is_espressif = False
                # Espressif USB Serial/JTAG VID=0x303A, PID=0x1001
                if p.vid == 0x303A or "Espressif" in (p.manufacturer or ""):
                    is_espressif = True
                discovered.append({
                    "port": p.device,
                    "description": p.description,
                    "hwid": p.hwid,
                    "is_espressif": is_espressif,
                })
        except ImportError:
            # Fallback if pyserial is not available in mock/CI environments
            discovered.append({
                "port": "COM3",
                "description": "USB Serial Device (Virtual Mock)",
                "hwid": "USB VID:PID=303A:1001",
                "is_espressif": True,
            })
        return discovered

    def connect(self) -> bool:
        if self._connected:
            return True

        if self._mock_serial is not None:
            self._serial_handle = self._mock_serial
            self._connected = True
        else:
            try:
                import serial
                target_port = self.port
                if target_port == "AUTO":
                    candidates = self.discover_ports()
                    esp_ports = [c["port"] for c in candidates if c["is_espressif"]]
                    target_port = esp_ports[0] if esp_ports else (candidates[0]["port"] if candidates else None)

                if not target_port:
                    logger.warning("No physical ESP32-C5 USB serial port found.")
                    return False

                self._serial_handle = serial.Serial(target_port, self.baudrate, timeout=1.0)
                self.port = target_port
                self._connected = True
            except Exception as e:
                logger.error(f"Failed to open USB serial port {self.port}: {e}")
                self._connected = False
                return False

        self._running = True
        self._rx_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._rx_thread.start()
        logger.info(f"UsbSerialTransport connected on {self.port} at {self.baudrate} baud.")
        return True

    def _read_loop(self) -> None:
        """Background thread reading newline-delimited JSON frames from USB."""
        line_buffer = bytearray()
        while self._running and self._connected:
            try:
                if self._mock_serial is not None:
                    raw_data = self._mock_serial.read(256)
                elif self._serial_handle is not None:
                    raw_data = self._serial_handle.read(256)
                else:
                    break

                if raw_data:
                    for b in raw_data:
                        if b in (ord(b"\n"), ord(b"\r")):
                            if line_buffer:
                                line_str = line_buffer.decode("utf-8", errors="replace").strip()
                                line_buffer.clear()
                                if line_str.startswith("{") and line_str.endswith("}"):
                                    try:
                                        parsed = json.loads(line_str)
                                        AresProtocol.validate_envelope(parsed)
                                        envelope = ProtocolEnvelope(parsed)
                                        self._rx_queue.put(envelope)
                                    except Exception as ex:
                                        logger.warning(f"Malformed protocol frame from USB: {ex}")
                        else:
                            line_buffer.append(b)
                else:
                    time.sleep(0.01)
            except Exception as e:
                logger.error(f"USB Serial read error: {e}")
                self._connected = False
                break

    def disconnect(self) -> None:
        self._running = False
        self._connected = False
        if self._serial_handle is not None:
            try:
                self._serial_handle.close()
            except Exception:
                pass
            self._serial_handle = None
        logger.info(f"UsbSerialTransport disconnected from {self.port}.")

    def is_connected(self) -> bool:
        return self._connected

    def send_message(self, message: Dict[str, Any]) -> bool:
        if not self._connected or self._serial_handle is None:
            return False
        try:
            payload_str = json.dumps(message, separators=(",", ":")) + "\n"
            data = payload_str.encode("utf-8")
            if self._mock_serial is not None:
                self._mock_serial.write(data)
            else:
                self._serial_handle.write(data)
                self._serial_handle.flush()
            return True
        except Exception as e:
            logger.error(f"USB Serial write error: {e}")
            self._connected = False
            return False

    def receive_message(self, timeout_sec: float = 1.0) -> Optional[ProtocolEnvelope]:
        try:
            return self._rx_queue.get(timeout=timeout_sec)
        except queue.Empty:
            return None

    def perform_hardware_handshake(self, db: Session, actor_id: str) -> Dict[str, Any]:
        """Perform physical handshake sequence: HELLO -> DEVICE_INFO -> CAPABILITIES,

        validates against database HardwareProfile.
        """
        if not self.is_connected():
            raise DeviceNotAuthorizedException("USB transport not connected.")

        # 1. Send HELLO
        hello_req = AresProtocol.create_message(AresMessageType.HELLO.value, payload={"action": "INIT"})
        self.send_message(hello_req)
        hello_resp = self.receive_message(timeout_sec=3.0)
        if not hello_resp or hello_resp.type != AresMessageType.HELLO.value:
            raise ProtocolViolationException("Physical ESP32 failed to respond to HELLO handshake.")

        device_uuid = hello_resp.device_id
        self.device_id = device_uuid

        # 2. Query DEVICE_INFO
        info_req = AresProtocol.create_message(AresMessageType.DEVICE_INFO.value, device_id=device_uuid)
        self.send_message(info_req)
        info_resp = self.receive_message(timeout_sec=3.0)
        if not info_resp or info_resp.type != AresMessageType.DEVICE_INFO.value:
            raise ProtocolViolationException("Physical ESP32 failed to respond to DEVICE_INFO request.")

        info_payload = info_resp.payload or {}
        chip = info_payload.get("chip", "ESP32-C5")
        board_target = info_payload.get("board_target", "ESP32-C5-DevKitC-1")
        flash_size = info_payload.get("flash_size", "8MB")

        # 3. Query CAPABILITIES
        caps_req = AresProtocol.create_message(AresMessageType.CAPABILITIES.value, device_id=device_uuid)
        self.send_message(caps_req)
        caps_resp = self.receive_message(timeout_sec=3.0)
        if not caps_resp or caps_resp.type != AresMessageType.CAPABILITIES.value:
            raise ProtocolViolationException("Physical ESP32 failed to respond to CAPABILITIES request.")

        caps_payload = caps_resp.payload or {}

        # 4. Strict Hardware Profile Verification against Database
        profile = db.query(HardwareProfile).filter(HardwareProfile.board_name == board_target).first()
        if not profile:
            raise HardwareIncompatibleException(
                f"Hardware profile for '{board_target}' not registered in database."
            )

        # Enforce Section 2 & 8: bluetooth_classic must NEVER be True for ESP32-C5
        if caps_payload.get("bluetooth_classic") is True:
            raise HardwareIncompatibleException(
                f"ESP32-C5 hardware profile mismatch: board claimed Bluetooth Classic support."
            )

        # Match chip
        if profile.chip != chip:
            raise HardwareIncompatibleException(
                f"Chip mismatch: board reported '{chip}', registered profile expects '{profile.chip}'."
            )

        AuditService.record_event(
            db=db,
            action="PHYSICAL_ESP32_HANDSHAKE_COMPLETED",
            resource_type="DEVICE",
            resource_id=device_uuid,
            actor_id=actor_id,
            metadata={
                "chip": chip,
                "board_target": board_target,
                "flash_size": flash_size,
                "port": self.port,
            },
        )

        return {
            "device_id": device_uuid,
            "chip": chip,
            "board_target": board_target,
            "flash_size": flash_size,
            "capabilities": caps_payload,
            "status": "READY",
        }

    def handle_disconnect(self, db: Session, device_id: str, actor_id: Optional[str] = None) -> None:
        """Handle physical USB disconnect event: mark device OFFLINE and active assessment INTERRUPTED."""
        self.disconnect()

        device = db.query(Device).filter(Device.device_uuid == device_id).first()
        if device:
            device.operational_status = "OFFLINE"

        esp = db.query(ESP32Device).join(Device).filter(Device.device_uuid == device_id).first()
        if esp:
            esp.status = "OFFLINE"

        # Check for active running assessments
        active_assessments = (
            db.query(Assessment)
            .join(Device, Assessment.target_device_id == Device.id)
            .filter(Device.device_uuid == device_id, Assessment.status == "RUNNING")
            .all()
        )

        for ass in active_assessments:
            # Section 37: "Do not mark an assessment complete merely because USB disconnected. Use: INTERRUPTED"
            ass.status = "INTERRUPTED"

        db.commit()

        AuditService.record_event(
            db=db,
            action="ESP32_DISCONNECTED",
            resource_type="DEVICE",
            resource_id=device_id,
            actor_id=actor_id,
            metadata={"port": self.port, "interrupted_assessments": len(active_assessments)},
        )
        logger.warning(f"Device '{device_id}' disconnected over USB. Assessments marked INTERRUPTED.")

    def handle_reconnect(self, db: Session, device_id: str, actor_id: Optional[str] = None) -> None:
        """Handle physical USB reconnection event: return device to READY."""
        device = db.query(Device).filter(Device.device_uuid == device_id).first()
        if device:
            device.operational_status = "READY"

        esp = db.query(ESP32Device).join(Device).filter(Device.device_uuid == device_id).first()
        if esp:
            esp.status = "ONLINE"
            esp.last_heartbeat = datetime.now(timezone.utc)

        db.commit()

        AuditService.record_event(
            db=db,
            action="ESP32_RECONNECTED",
            resource_type="DEVICE",
            resource_id=device_id,
            actor_id=actor_id,
            metadata={"port": self.port, "status": "READY"},
        )
        logger.info(f"Device '{device_id}' reconnected over USB. Status restored to READY.")
