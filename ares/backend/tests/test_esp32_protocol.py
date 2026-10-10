"""Tests for ARES/1.0 Protocol and ESP32-C5 Hardware Profile."""
import pytest
from app.core.exceptions import InvalidProtocolMessageException, UnknownCommandException
from app.esp32.capability_parser import CapabilityParser
from app.esp32.protocol import AresProtocol
from app.esp32.simulator import ESP32Simulator


def test_protocol_envelope_creation_and_validation():
    msg = AresProtocol.create_message(
        message_type="HELLO",
        device_id="DEV-001",
        payload={"chip": "ESP32-C5"},
        sequence=1,
    )
    assert msg["protocol"] == "ARES/1.0"
    assert msg["type"] == "HELLO"

    is_valid, reason = AresProtocol.validate_envelope(msg)
    assert is_valid is True
    assert reason == "Valid"


def test_command_whitelist_enforcement():
    # Allowed command
    AresProtocol.validate_command("WIFI_SCAN_START")

    # Disallowed command must raise UnknownCommandException
    with pytest.raises(UnknownCommandException):
        AresProtocol.validate_command("UNAUTHORIZED_DEAUTH_ATTACK")

    with pytest.raises(UnknownCommandException):
        AresProtocol.validate_command("ARBITRARY_SHELL_EXEC")


def test_esp32_c5_capability_parser_boundaries():
    raw_caps = {
        "chip": "ESP32-C5",
        "board": "ESP32-C5-DevKitC-1",
        "flash": "8MB",
        "psram": "8MB",
    }
    parsed = CapabilityParser.parse_esp32_c5_devkit(raw_caps)
    # Hardware boundaries must hold:
    assert parsed["bluetooth_classic"] is False
    assert parsed["wifi_24"] is True
    assert parsed["wifi_5"] is True
    assert parsed["wifi6"] is True
    assert parsed["ble"] is True
    assert parsed["peripheral_pinouts"]["microsd_spi"]["miso"] == "GPIO2"
    assert parsed["peripheral_pinouts"]["microsd_spi"]["cs"] == "GPIO10"


def test_esp32_simulator_scans():
    sim = ESP32Simulator()
    wifi_res = sim.simulate_wifi_scan()
    assert wifi_res["type"] == "WIFI_SCAN_RESULT"
    networks = wifi_res["payload"]["networks"]
    assert len(networks) > 0
    bands = {n["band"] for n in networks}
    assert "2.4GHz" in bands
    assert "5GHz" in bands

    ble_res = sim.simulate_ble_scan()
    assert ble_res["type"] == "BLE_SCAN_RESULT"
    assert len(ble_res["payload"]["devices"]) > 0
