"""Security Audit Tests: ARES/1.0 Protocol Security & Envelope Validation (Section 10)."""
import time
import pytest
from app.esp32.protocol import AresProtocol, AresMessage, AresMessageType, AresCommandType
from app.core.exceptions import ProtocolViolationException


SECRET = "super-secret-hmac-key-for-test-32b"


def test_unknown_message_type_rejected():
    """Verify that envelopes with unknown message types are rejected."""
    msg = AresMessage(
        protocol="ARES/1.0",
        message_id="msg-unk-01",
        device_id="esp32-test",
        timestamp=int(time.time()),
        type="NON_EXISTENT_TYPE",
        sequence=1,
        payload={},
    )
    with pytest.raises(ProtocolViolationException) as exc_info:
        AresProtocol.validate_envelope(msg, hmac_secret=SECRET)
    assert "unknown message type" in str(exc_info.value).lower()


def test_unknown_command_type_rejected():
    """Verify that command execution rejects unknown/illegal command strings."""
    with pytest.raises(ProtocolViolationException) as exc_info:
        AresProtocol.validate_command("DEAUTH_ATTACK", {})
    assert "unknown command" in str(exc_info.value).lower()


def test_invalid_signature_rejected():
    """Verify that messages with invalid HMAC signature are rejected."""
    msg = AresProtocol.create_message(
        device_id="esp32-01",
        msg_type=AresMessageType.TELEMETRY,
        payload={"battery_mv": 3700},
        sequence=1,
        hmac_secret=SECRET,
    )
    # Tamper with the signature
    msg.signature = "badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadb"
    
    with pytest.raises(ProtocolViolationException) as exc_info:
        AresProtocol.validate_envelope(msg, hmac_secret=SECRET)
    assert "invalid signature" in str(exc_info.value).lower()


def test_oversized_payload_rejected():
    """Verify that payloads exceeding the 64KB protocol boundary are rejected."""
    large_payload = {"junk_data": "A" * 70000}
    
    with pytest.raises(ProtocolViolationException) as exc_info:
        AresProtocol.create_message(
            device_id="esp32-01",
            msg_type=AresMessageType.DATA_OBSERVATION,
            payload=large_payload,
            sequence=1,
            hmac_secret=SECRET,
        )
    assert "payload exceeds maximum limit" in str(exc_info.value).lower()


def test_tampered_payload_detected():
    """Verify that altering payload content breaks the HMAC signature check."""
    msg = AresProtocol.create_message(
        device_id="esp32-01",
        msg_type=AresMessageType.DATA_OBSERVATION,
        payload={"rssi": -45, "channel": 1},
        sequence=1,
        hmac_secret=SECRET,
    )
    # Modify payload in transit
    msg.payload["channel"] = 6

    with pytest.raises(ProtocolViolationException) as exc_info:
        AresProtocol.validate_envelope(msg, hmac_secret=SECRET)
    assert "invalid signature" in str(exc_info.value).lower()
