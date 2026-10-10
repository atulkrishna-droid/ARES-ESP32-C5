# ARES/1.0 Firmware Wire Protocol Specification

## 1. Frame Envelope
All messages transmitted between the host backend and ESP32-C5 use newline-delimited (`\n`) JSON frames conforming to ARES/1.0:

```json
{
  "protocol": "ARES/1.0",
  "message_id": "msg-4a12be7c",
  "device_id": "ares-esp32-c5-aabbccddeeff",
  "timestamp": "2026-09-27T18:45:00Z",
  "type": "HELLO",
  "sequence": 1,
  "payload": {
    "protocol_version": "ARES/1.0",
    "firmware_version": "1.0.0",
    "board_target": "ESP32-C5-DevKitC-1",
    "status": "READY"
  },
  "signature": "3f9a72b..."
}
```

## 2. Command Types & Workflows
1. `HELLO`: Mutual handshake and protocol identification.
2. `DEVICE_INFO`: Chip revision, flash size, MAC, uptime, memory metrics.
3. `CAPABILITIES`: Explicit hardware capabilities report.
4. `HEARTBEAT`: Periodic 5-second health ping with radio states.
5. `WIFI_SCAN_START` / `WIFI_SCAN_STOP`: Trigger authorized dual-band 2.4/5GHz AP discovery.
6. `BLE_SCAN_START` / `BLE_SCAN_STOP`: Trigger BLE advertising discovery.
7. `STOP`: High-priority safety abort.
