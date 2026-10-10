"""Tests for Physical ESP32 Host Transport (UsbSerialTransport and SimulatorTransport)."""
import json
import queue
from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import (
    HardwareIncompatibleException,
    ProtocolViolationException,
)
from app.esp32.physical_transport import Esp32Transport, SimulatorTransport, UsbSerialTransport
from app.esp32.protocol import AresMessageType, AresProtocol
from app.esp32.simulator import ESP32C5Simulator
from app.models.assessment import Assessment
from app.models.case import Case
from app.models.device import Device, DeviceAuthorization
from app.models.esp32_device import ESP32Device
from app.models.hardware_profile import HardwareProfile
from app.models.user import User


class MockSerialPort:
    """Simulates a bidirectional USB Serial/JTAG port connected to a physical ESP32-C5."""

    def __init__(self, device_id: str = "ares-esp32-c5-aabbccddeeff"):
        self.device_id = device_id
        self.inbox: queue.Queue = queue.Queue()
        self.outbox: queue.Queue = queue.Queue()
        self.is_open = True
        self.simulate_rogue_profile = False
        self.tx_seq = 1

    def write(self, data: bytes) -> int:
        lines = data.decode("utf-8").strip().split("\n")
        for line in lines:
            if not line:
                continue
            try:
                msg = json.loads(line)
                mtype = msg.get("type")
                seq = self.tx_seq
                self.tx_seq += 1
                if mtype == AresMessageType.HELLO.value:
                    resp = AresProtocol.create_message(
                        AresMessageType.HELLO.value,
                        payload={
                            "protocol_version": "ARES/1.0",
                            "firmware_version": "1.0.0",
                            "status": "READY",
                        },
                        device_id=self.device_id,
                        sequence=seq,
                    )
                    self.inbox.put(json.dumps(resp).encode("utf-8") + b"\n")

                elif mtype == AresMessageType.DEVICE_INFO.value:
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
                        sequence=seq,
                    )
                    self.inbox.put(json.dumps(resp).encode("utf-8") + b"\n")

                elif mtype == AresMessageType.CAPABILITIES.value:
                    # Accurately reflect ESP32-C5: bluetooth_classic = False
                    resp = AresProtocol.create_message(
                        AresMessageType.CAPABILITIES.value,
                        payload={
                            "wifi_24": True,
                            "wifi_5": True,
                            "wifi6": True,
                            "ble": True,
                            "bluetooth_classic": True if self.simulate_rogue_profile else False,
                            "ieee802154": True,
                            "usb": True,
                            "sd": False,
                            "gps": False,
                            "battery": False,
                            "display": False,
                        },
                        device_id=self.device_id,
                        sequence=seq,
                    )
                    self.inbox.put(json.dumps(resp).encode("utf-8") + b"\n")

            except Exception:
                pass
        return len(data)

    def read(self, size: int = 256) -> bytes:
        try:
            return self.inbox.get(timeout=0.1)
        except queue.Empty:
            return b""

    def close(self) -> None:
        self.is_open = False


def test_simulator_transport_lifecycle():
    """Verify SimulatorTransport satisfies Esp32Transport interface identically to physical."""
    transport = SimulatorTransport(device_id="ESP32-C5-TEST-SIM")
    assert isinstance(transport, Esp32Transport)
    assert transport.connect() is True
    assert transport.is_connected() is True

    # Send HELLO
    hello_req = AresProtocol.create_message(AresMessageType.HELLO.value)
    assert transport.send_message(hello_req) is True

    resp = transport.receive_message(timeout_sec=2.0)
    assert resp is not None
    assert resp.type == AresMessageType.HELLO.value
    assert resp.device_id == "ESP32-C5-TEST-SIM"

    transport.disconnect()
    assert transport.is_connected() is False


def test_usb_serial_port_discovery():
    """Verify UsbSerialTransport discovers ports and parses Espressif VID/PID."""
    ports = UsbSerialTransport.discover_ports()
    assert isinstance(ports, list)
    assert len(ports) > 0
    assert any("port" in p for p in ports)


def test_physical_hardware_handshake_flow(db_session: Session):
    """Verify physical USB handshake sequence: HELLO -> DEVICE_INFO -> CAPABILITIES."""
    import uuid
    admin = User(
        username=f"admin_{uuid.uuid4().hex[:6]}",
        email=f"admin_{uuid.uuid4().hex[:6]}@ares.security",
        password_hash="dummy_hash_for_test",
        display_name="Admin Test",
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    # Ensure standard profile exists
    profile = db_session.query(HardwareProfile).filter(HardwareProfile.board_name == "ESP32-C5-DevKitC-1").first()
    if not profile:
        profile = HardwareProfile(
            name="ESP32-C5-DevKitC-1 Standard Profile",
            board_name="ESP32-C5-DevKitC-1",
            chip="ESP32-C5",
            wifi_24=True,
            wifi_5=True,
            wifi6=True,
            ble=True,
            bluetooth_classic=False,
            ieee802154=True,
            usb=True,
        )
        db_session.add(profile)
        db_session.commit()

    mock_port = MockSerialPort(device_id="ares-esp32-c5-112233445566")
    transport = UsbSerialTransport(port="COM4", mock_serial=mock_port)
    assert transport.connect() is True

    handshake_result = transport.perform_hardware_handshake(db=db_session, actor_id=admin.id)
    assert handshake_result["status"] == "READY"
    assert handshake_result["chip"] == "ESP32-C5"
    assert handshake_result["board_target"] == "ESP32-C5-DevKitC-1"
    assert handshake_result["capabilities"]["bluetooth_classic"] is False
    assert handshake_result["capabilities"]["wifi6"] is True

    transport.disconnect()


def test_rogue_device_bluetooth_classic_rejection(db_session: Session):
    """Verify Section 2 & 8: firmware claiming Bluetooth Classic on ESP32-C5 is rejected."""
    profile = db_session.query(HardwareProfile).filter(HardwareProfile.board_name == "ESP32-C5-DevKitC-1").first()
    if not profile:
        profile = HardwareProfile(
            name="ESP32-C5-DevKitC-1 Standard Profile",
            board_name="ESP32-C5-DevKitC-1",
            chip="ESP32-C5",
            wifi_24=True,
            wifi_5=True,
            wifi6=True,
            ble=True,
            bluetooth_classic=False,
            ieee802154=True,
            usb=True,
        )
        db_session.add(profile)
        db_session.commit()

    mock_port = MockSerialPort(device_id="ares-esp32-c5-rogue01")
    mock_port.simulate_rogue_profile = True  # Rogue profile claiming BT Classic
    transport = UsbSerialTransport(port="COM5", mock_serial=mock_port)
    transport.connect()

    with pytest.raises(HardwareIncompatibleException) as exc:
        transport.perform_hardware_handshake(db=db_session, actor_id=None)

    assert "Bluetooth Classic" in str(exc.value)
    transport.disconnect()


def test_usb_disconnect_and_assessment_interruption(db_session: Session):
    """Verify Section 37: USB disconnect sets device OFFLINE and active assessment to INTERRUPTED."""
    import uuid
    user = User(
        username=f"op_{uuid.uuid4().hex[:6]}",
        email=f"op_{uuid.uuid4().hex[:6]}@ares.security",
        password_hash="dummy_password_hash",
        display_name="Operator User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    device = Device(
        device_uuid=f"ares-esp32-c5-{uuid.uuid4().hex[:8]}",
        device_type="ESP32",
        environment="PHYSICAL",
        operational_status="READY",
    )
    db_session.add(device)
    db_session.flush()

    esp = ESP32Device(device_id=device.id, chip="ESP32-C5", board_name="ESP32-C5-DevKitC-1", status="ONLINE")
    db_session.add(esp)

    case = Case(
        case_number=f"CASE-USB-{uuid.uuid4().hex[:6]}",
        title="USB Test Case",
        created_by=user.id,
    )
    db_session.add(case)
    db_session.flush()

    assessment = Assessment(
        case_id=case.id,
        target_device_id=device.id,
        assessment_type="WIFI_DISCOVERY",
        status="RUNNING",
        created_by=user.id,
    )
    db_session.add(assessment)
    db_session.commit()

    mock_port = MockSerialPort(device_id=device.device_uuid)
    transport = UsbSerialTransport(port="COM6", mock_serial=mock_port)
    transport.connect()

    # Trigger USB disconnect
    transport.handle_disconnect(db=db_session, device_id=device.device_uuid)

    db_session.refresh(device)
    db_session.refresh(esp)
    db_session.refresh(assessment)

    assert device.operational_status == "OFFLINE"
    assert esp.status == "OFFLINE"
    # Section 37 requirement: Use INTERRUPTED rather than COMPLETED
    assert assessment.status == "INTERRUPTED"

    # Reconnect
    transport.handle_reconnect(db=db_session, device_id=device.device_uuid)
    db_session.refresh(device)
    assert device.operational_status == "READY"
