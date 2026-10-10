"""Security Audit Tests: Replay Protection & Sequence Monotonicity (Section 12)."""
import time
import pytest
from app.esp32.protocol import AresProtocol, AresMessage, AresMessageType
from app.core.exceptions import ProtocolViolationException


SECRET = "replay-defense-test-secret-key-32b"


def setup_function():
    """Reset sequence tracker before each test."""
    AresProtocol._device_sequences.clear()


def test_monotonic_sequence_accepted():
    """Verify that messages with strictly increasing sequence numbers are accepted."""
    msg1 = AresProtocol.create_message("dev-seq-1", AresMessageType.HELLO, {"uptime": 1}, sequence=1, hmac_secret=SECRET)
    AresProtocol.validate_envelope(msg1, hmac_secret=SECRET)

    msg2 = AresProtocol.create_message("dev-seq-1", AresMessageType.TELEMETRY, {"uptime": 2}, sequence=2, hmac_secret=SECRET)
    AresProtocol.validate_envelope(msg2, hmac_secret=SECRET)


def test_replayed_sequence_rejected():
    """Verify that replaying the same sequence number is detected and rejected."""
    msg1 = AresProtocol.create_message("dev-seq-2", AresMessageType.HELLO, {"uptime": 10}, sequence=1, hmac_secret=SECRET)
    AresProtocol.validate_envelope(msg1, hmac_secret=SECRET)

    # Replay same message / same sequence number
    with pytest.raises(ProtocolViolationException) as exc_info:
        AresProtocol.validate_envelope(msg1, hmac_secret=SECRET)
    assert "replay detected" in str(exc_info.value).lower() or "sequence" in str(exc_info.value).lower()


def test_lower_sequence_number_rejected():
    """Verify that an older/lower sequence number arrives out of order is rejected."""
    msg2 = AresProtocol.create_message("dev-seq-3", AresMessageType.HELLO, {"uptime": 10}, sequence=5, hmac_secret=SECRET)
    AresProtocol.validate_envelope(msg2, hmac_secret=SECRET)

    msg_older = AresProtocol.create_message("dev-seq-3", AresMessageType.TELEMETRY, {"uptime": 11}, sequence=3, hmac_secret=SECRET)
    with pytest.raises(ProtocolViolationException) as exc_info:
        AresProtocol.validate_envelope(msg_older, hmac_secret=SECRET)
    assert "sequence" in str(exc_info.value).lower()


def test_expired_old_timestamp_rejected():
    """Verify that messages with timestamp older than 60 seconds are rejected."""
    old_time = int(time.time()) - 75
    msg = AresMessage(
        protocol="ARES/1.0",
        message_id="msg-old-ts",
        device_id="dev-ts-test",
        timestamp=old_time,
        type="TELEMETRY",
        sequence=1,
        payload={"rssi": -60},
    )
    msg.signature = AresProtocol.compute_signature(msg.to_dict(), SECRET)

    with pytest.raises(ProtocolViolationException) as exc_info:
        AresProtocol.validate_envelope(msg, hmac_secret=SECRET)
    assert "timestamp clock skew" in str(exc_info.value).lower() or "expired" in str(exc_info.value).lower()


def test_future_timestamp_rejected():
    """Verify that messages with timestamp > 60s into the future are rejected."""
    future_time = int(time.time()) + 75
    msg = AresMessage(
        protocol="ARES/1.0",
        message_id="msg-future-ts",
        device_id="dev-ts-test",
        timestamp=future_time,
        type="TELEMETRY",
        sequence=1,
        payload={"rssi": -60},
    )
    msg.signature = AresProtocol.compute_signature(msg.to_dict(), SECRET)

    with pytest.raises(ProtocolViolationException) as exc_info:
        AresProtocol.validate_envelope(msg, hmac_secret=SECRET)
    assert "clock skew" in str(exc_info.value).lower()
