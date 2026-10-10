# ARES ESP32-C5 Firmware Security Controls

## 1. Cryptographic Authentication
- Every ARES/1.0 command and response is authenticated using `HMAC-SHA256` computed via hardware-accelerated mbedTLS.
- Canonical signing string:
  `{protocol}|{type}|{device_id}|{timestamp}|{sequence}|{canonical_payload}`
- Constant-time memory comparison (`constant_time_memcmp`) prevents timing side-channel attacks.

## 2. Replay Protection
- Strictly monotonic sequence verification: any incoming message with `sequence <= last_rx_sequence` is rejected immediately with error code `INVALID_SEQUENCE`.
- Clock skew window ($\pm 60$ seconds) prevents execution of delayed or replayed packets.

## 3. Command Whitelist
- Only pre-approved assessment commands (`HELLO`, `DEVICE_INFO`, `CAPABILITIES`, `HEARTBEAT`, `GET_STATUS`, `WIFI_SCAN_START/STOP`, `BLE_SCAN_START/STOP`, `STOP`) are permitted.
- Shell access, arbitrary code execution, and unverified OTA flashing are blocked.
