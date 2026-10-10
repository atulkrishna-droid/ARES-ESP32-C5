# ARES/1.0 Protocol Specification

## Overview
ARES/1.0 is the hardware communication protocol between the ARES backend and the ESP32-C5 security peripheral (as well as the software simulator). It enforces strict command whitelisting, sequence tracking, message timestamp windows, and signature verification.

---

## Message Envelope Structure

All communications use structured envelopes formatted as canonical JSON:

```json
{
  "protocol": "ARES/1.0",
  "message_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "device_id": "ESP32-C5-DEVKIT-001",
  "timestamp": "2026-09-27T12:00:00Z",
  "type": "WIFI_SCAN_RESULT",
  "sequence": 42,
  "payload": {},
  "signature": "UNSIGNED"
}
```

### Envelope Fields
| Field | Type | Description |
|---|---|---|
| `protocol` | string | Constant `"ARES/1.0"` |
| `message_id` | string (UUID) | Unique message identifier |
| `device_id` | string | Enrolled hardware UUID |
| `timestamp` | string (ISO-8601 UTC) | Message generation timestamp. Replay window: +/- 300s |
| `type` | string | Command or event name from strict whitelist |
| `sequence` | integer | Incrementing sequence number |
| `payload` | object | Command/telemetry data |
| `signature` | string | HMAC-SHA256 of canonical envelope |

---

## Allowed Command Whitelist
The backend explicitly rejects any command not in this whitelist with `COMMAND_REJECTED`:

- **Handshake & Identification**: `HELLO`, `DEVICE_INFO`, `CAPABILITIES`, `PAIR_REQUEST`, `PAIR_RESPONSE`, `AUTH_CHALLENGE`, `AUTH_RESPONSE`, `HEARTBEAT`
- **Wi-Fi Reconnaissance**: `WIFI_SCAN_START`, `WIFI_SCAN_STOP`, `WIFI_SCAN_PROGRESS`, `WIFI_SCAN_RESULT`, `WIFI_SCAN_COMPLETE`
- **BLE Reconnaissance**: `BLE_SCAN_START`, `BLE_SCAN_STOP`, `BLE_SCAN_PROGRESS`, `BLE_SCAN_RESULT`, `BLE_SCAN_COMPLETE`
- **Telemetry & Hardware Status**: `SD_STATUS`, `TELEMETRY`, `GET_STATUS`, `GET_CAPABILITIES`, `GET_STORAGE_STATUS`, `GET_FIRMWARE_INFO`, `STOP`, `ERROR`

---

## Hardware Target: ESP32-C5-DevKitC-1
- Dual-band 2.4 GHz + 5 GHz (Wi-Fi 6) observations.
- Passive Bluetooth Low Energy advertisement collection.
- `bluetooth_classic = False` is enforced by backend capability parsers.
- External microSD module pinouts:
  - `MISO`: `GPIO2`
  - `MOSI`: `GPIO7`
  - `SCK`: `GPIO6`
  - `CS`: `GPIO10`
