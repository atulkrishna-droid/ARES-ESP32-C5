"""ARES/1.0 Hardware and Device Protocol Specification and Validator."""
from enum import Enum
import hmac
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from app.core.constants import ALLOWED_ESP32_COMMANDS
from app.core.exceptions import (
    InvalidProtocolMessageException,
    ProtocolViolationException,
    UnknownCommandException,
)
from app.core.security import canonical_json_bytes, sha256_hash


class AresMessageType(str, Enum):
    HELLO = "HELLO"
    DEVICE_INFO = "DEVICE_INFO"
    CAPABILITIES = "CAPABILITIES"
    PAIR_REQUEST = "PAIR_REQUEST"
    PAIR_RESPONSE = "PAIR_RESPONSE"
    AUTH_CHALLENGE = "AUTH_CHALLENGE"
    AUTH_RESPONSE = "AUTH_RESPONSE"
    HEARTBEAT = "HEARTBEAT"
    WIFI_SCAN_START = "WIFI_SCAN_START"
    WIFI_SCAN_STOP = "WIFI_SCAN_STOP"
    WIFI_SCAN_PROGRESS = "WIFI_SCAN_PROGRESS"
    WIFI_SCAN_RESULT = "WIFI_SCAN_RESULT"
    WIFI_SCAN_COMPLETE = "WIFI_SCAN_COMPLETE"
    BLE_SCAN_START = "BLE_SCAN_START"
    BLE_SCAN_STOP = "BLE_SCAN_STOP"
    BLE_SCAN_PROGRESS = "BLE_SCAN_PROGRESS"
    BLE_SCAN_RESULT = "BLE_SCAN_RESULT"
    BLE_SCAN_COMPLETE = "BLE_SCAN_COMPLETE"
    SD_STATUS = "SD_STATUS"
    TELEMETRY = "TELEMETRY"
    ASSESSMENT_START = "ASSESSMENT_START"
    ASSESSMENT_PROGRESS = "ASSESSMENT_PROGRESS"
    ASSESSMENT_FINDING = "ASSESSMENT_FINDING"
    ASSESSMENT_COMPLETE = "ASSESSMENT_COMPLETE"
    ERROR = "ERROR"
    STOP = "STOP"
    DATA_OBSERVATION = "WIFI_SCAN_RESULT"


AresCommandType = AresMessageType


class ProtocolEnvelope(dict):
    """Protocol envelope supporting both dict item access and dot-attribute access."""
    def __getattr__(self, name: str) -> Any:
        try:
            val = self[name]
            if isinstance(val, dict) and not isinstance(val, ProtocolEnvelope):
                val = ProtocolEnvelope(val)
                self[name] = val
            return val
        except KeyError:
            raise AttributeError(f"'ProtocolEnvelope' has no attribute '{name}'")

    def __setattr__(self, name: str, val: Any) -> None:
        self[name] = val

    def to_dict(self) -> Dict[str, Any]:
        return dict(self)


def AresMessage(**kwargs) -> ProtocolEnvelope:
    return ProtocolEnvelope(kwargs)


class AresProtocol:
    PROTOCOL_VERSION = "ARES/1.0"
    MAX_CLOCK_SKEW_SECONDS = 60   # Canonical ARES/1.0 tolerance (±60 seconds)
    MAX_PAYLOAD_BYTES = 65536     # 64 KB maximum payload limit

    # In-memory sequence tracking for replay defense per device
    _seen_sequences: Dict[str, int] = {}
    _device_sequences: Dict[str, int] = _seen_sequences

    @classmethod
    def reset_sequence_tracking(cls, device_id: Optional[str] = None) -> None:
        if device_id:
            cls._seen_sequences.pop(device_id, None)
        else:
            cls._seen_sequences.clear()

    @classmethod
    def compute_signature(cls, message: Dict[str, Any], signing_key: str) -> str:
        """Compute SHA256 HMAC of canonical message payload without signature field."""
        copy_msg = dict(message)
        copy_msg.pop("signature", None)
        return hmac.new(signing_key.encode("utf-8"), canonical_json_bytes(copy_msg), "sha256").hexdigest()

    @classmethod
    def create_message(
        cls,
        *args,
        message_type: Optional[str] = None,
        device_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        sequence: int = 1,
        signing_key: Optional[str] = None,
        hmac_secret: Optional[str] = None,
        msg_type: Optional[str] = None,
        **kwargs,
    ) -> ProtocolEnvelope:
        """Create a compliant ARES/1.0 message envelope supporting multiple invocation signatures."""
        key = signing_key or hmac_secret

        if len(args) == 3:
            device_id, message_type, payload = args
        elif len(args) == 2:
            device_id, message_type = args
        elif len(args) == 1:
            message_type = args[0]

        message_type = message_type or msg_type
        if isinstance(message_type, Enum):
            message_type = message_type.value

        if payload is None:
            payload = kwargs.get("payload", {})

        cls.validate_command(message_type)

        # Check payload size bounds at creation time
        payload_bytes = canonical_json_bytes(payload)
        if len(payload_bytes) > cls.MAX_PAYLOAD_BYTES:
            raise ProtocolViolationException(
                f"Payload exceeds maximum limit of {cls.MAX_PAYLOAD_BYTES} bytes (got {len(payload_bytes)} bytes)."
            )

        msg_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        msg = ProtocolEnvelope({
            "protocol": cls.PROTOCOL_VERSION,
            "message_id": msg_id,
            "device_id": device_id or "UNKNOWN",
            "timestamp": timestamp,
            "type": message_type,
            "sequence": sequence,
            "payload": payload,
        })

        if key:
            msg["signature"] = cls.compute_signature(msg, key)
        else:
            msg["signature"] = "UNSIGNED"

        return msg

    @classmethod
    def validate_command(cls, command: Any, extra_payload: Any = None) -> None:
        """Validate command against strict whitelist."""
        if isinstance(command, Enum):
            cmd_str = command.value
        else:
            cmd_str = str(command)

        if cmd_str not in ALLOWED_ESP32_COMMANDS:
            raise UnknownCommandException(f"Unknown command '{cmd_str}' is not in allowed ARES command set.")

    @classmethod
    def validate_envelope(
        cls,
        message: Dict[str, Any],
        signing_key: Optional[str] = None,
        enforce_sequence: bool = True,
        hmac_secret: Optional[str] = None,
        raise_on_error: bool = True,
    ) -> Tuple[bool, str]:
        """Validate envelope format, timestamps, sequence numbers, payload size, and signature."""
        key = signing_key or hmac_secret

        def _fail(reason: str):
            if raise_on_error:
                raise ProtocolViolationException(reason)
            return False, reason

        for field in ("protocol", "message_id", "device_id", "timestamp", "type", "sequence", "payload"):
            if field not in message:
                return _fail(f"Missing required envelope field: {field}")

        if message.get("protocol") != cls.PROTOCOL_VERSION:
            return _fail(f"Unsupported protocol version: {message.get('protocol')}")

        try:
            cls.validate_command(message.get("type"))
        except UnknownCommandException as exc:
            return _fail(f"Unknown message type: {str(exc)}")

        # Payload size bounds
        payload_bytes = canonical_json_bytes(message.get("payload", {}))
        if len(payload_bytes) > cls.MAX_PAYLOAD_BYTES:
            return _fail(f"Payload exceeds maximum limit of {cls.MAX_PAYLOAD_BYTES} bytes (got {len(payload_bytes)} bytes).")

        # Verify signature if key is configured (BEFORE sequence checks)
        if key:
            received_sig = message.get("signature")
            if not received_sig or received_sig == "UNSIGNED":
                return _fail("Message signature is missing or unsigned.")
            expected_sig = cls.compute_signature(message, key)
            if not hmac.compare_digest(received_sig, expected_sig):
                return _fail("Invalid signature.")

        # Timestamp validation for replay defense
        ts_val = message["timestamp"]
        try:
            if isinstance(ts_val, (int, float)):
                msg_dt = datetime.fromtimestamp(ts_val, tz=timezone.utc)
            elif isinstance(ts_val, str):
                msg_dt = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
            else:
                return _fail("Invalid timestamp format.")
        except Exception:
            return _fail("Invalid timestamp format.")

        now_dt = datetime.now(timezone.utc)
        delta = abs((now_dt - msg_dt).total_seconds())
        if delta > cls.MAX_CLOCK_SKEW_SECONDS:
            return _fail(f"Message timestamp clock skew ({delta:.1f}s > {cls.MAX_CLOCK_SKEW_SECONDS}s) - expired or future.")

        # Sequence number replay check
        device_id = message.get("device_id")
        seq = message.get("sequence")
        if not isinstance(seq, int) or seq < 1:
            return _fail("Sequence number must be a positive integer.")

        if enforce_sequence and device_id:
            last_seq = cls._seen_sequences.get(device_id, 0)
            if seq <= last_seq:
                return _fail(f"Replayed or out-of-order sequence number ({seq} <= {last_seq})")
            cls._seen_sequences[device_id] = seq

        return True, "Valid"
