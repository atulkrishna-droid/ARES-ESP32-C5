# ARES ESP32-C5 Testing Guide (Host & Hardware-in-the-Loop)

## 1. Automated Host-Side Tests
The ARES backend includes automated tests validating the transport layer and protocol state machine:
```bash
pytest tests/test_physical_transport.py -v
```

Tests cover:
- UsbSerialTransport with mock serial driver
- Handshake protocol sequence (`HELLO` -> `DEVICE_INFO` -> `CAPABILITIES`)
- Hardware profile validation and rejection of rogue devices
- Replay detection and clock skew rejection
- Clean disconnect handling (`OFFLINE`, active assessment marked `INTERRUPTED`)
- Clean reconnect handling (`READY`)

## 2. Hardware-in-the-Loop Test Plan (Physical ESP32-C5)
When physical hardware is connected:
1. **TEST 1**: USB device detection (`VID:PID=303A:1001`).
2. **TEST 2**: Firmware boot and automatic `HELLO` dispatch.
3. **TEST 3**: Query `DEVICE_INFO` (verify chip reports "ESP32-C5").
4. **TEST 4**: Query `CAPABILITIES` (verify `bluetooth_classic = false`).
5. **TEST 5**: Mutual HMAC authentication.
6. **TEST 6**: Periodic 5-second `HEARTBEAT` reception.
7. **TEST 7**: Dual-band Wi-Fi scan on 2.4/5GHz (`WIFI_SCAN_START`).
8. **TEST 8**: BLE discovery scan (`BLE_SCAN_START`).
9. **TEST 9**: High-priority `STOP` command execution.
10. **TEST 10**: Physical USB disconnect and reconnect resilience.
11. **TEST 11**: Rejection of unknown commands.
12. **TEST 12**: Rejection of replayed sequence counters.
