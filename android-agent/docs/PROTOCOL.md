# ARES Android Agent — Protocol Specification

## 1. Protocol Overview

The Android Agent uses the identical `ARES/1.0` wire protocol envelope used by the physical ESP32-C5 firmware and simulator:

```json
{
  "protocol": "ARES/1.0",
  "message_id": "urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "device_id": "ares-android-11223344",
  "timestamp": "2026-09-27T14:30:00Z",
  "type": "HELLO",
  "sequence": 1,
  "payload": {
    "protocol_version": "ARES/1.0",
    "device_type": "ANDROID",
    "enrollment_id": "d9b2d63d-a233-4f9e-a67b-f9a8b1399432"
  },
  "signature": "3b29c9a5..."
}
```

---

## 2. Whitelisted Message Types

| Message Type | Direction | Description |
|---|---|---|
| `HELLO` | Agent $\to$ Host | Initial registration handshake declaring identity and enrollment ID. |
| `DEVICE_INFO` | Host $\leftrightarrow$ Agent | Ingestion of Android version, SDK, manufacturer, and model. |
| `CAPABILITIES` | Host $\leftrightarrow$ Agent | Query and response of legitimately supported platform capabilities. |
| `HEARTBEAT` | Agent $\to$ Host | Periodic alive ping (5–10s) with active state and VPN/developer indicators. |
| `GET_STATUS` | Host $\to$ Agent | Queries current operational state (`OFFLINE`, `AUTHORIZED`, `BUSY`, etc.). |
| `GET_TELEMETRY` | Host $\to$ Agent | Pulls current memory, network, and battery status. |
| `ASSESSMENT_START` | Host $\to$ Agent | Dispatches authorized assessment execution within active case scope. |
| `ASSESSMENT_STOP` | Host $\to$ Agent | Halts running assessment and returns to `AUTHORIZED` state. |
| `ASSESSMENT_RESULT` | Agent $\to$ Host | Returns array of deterministic findings. |
| `EVIDENCE_METADATA` | Agent $\to$ Host | Ingests cryptographic evidence metadata (SHA-256 and SHA-512). |
| `ERROR` | Both | Standardized error frames with specific code. |

---

## 3. Replay Protection & Sequence Monotonicity

- Every frame transmitted advances the monotonic sequence counter.
- Timestamps with clock skew exceeding 60 seconds ($\pm 60$ seconds) are rejected with `TIMESTAMP_EXPIRED`.

---

## 4. Cryptographic Authentication Model

- **Algorithm**: `HMAC-SHA256` (symmetric pre-shared key or enrolled device secret).
- **Interoperability**: Identical to the ESP32-C5 firmware and backend `AresProtocol.compute_signature`.
- **Wire Representation**: 64-character lowercase hexadecimal string in the `signature` field.
- **Canonical Input**: Canonical JSON string or delimited header with payload, excluding the `signature` key.
- **Android Keystore**: The HMAC-SHA256 secret is safely generated and retained in Android Keystore / encrypted preferences, never exported in plaintext. No asymmetric/ECDSA signatures are used on the wire.
