# ARES ESP32-C5 Firmware — System Architecture

```
                  ┌──────────────────────────────────────┐
                  │          ESP32-C5-DevKitC-1          │
                  │   RISC-V 32-bit Single-Core / 8MB    │
                  └──────────────────┬───────────────────┘
                                     │
                 ┌───────────────────┼───────────────────┐
                 │                   │                   │
                 ▼                   ▼                   ▼
       ┌──────────────────┐ ┌──────────────────┐ ┌───────────────┐
       │   Radio Layers   │ │   FreeRTOS Tasks │ │ Security & NV │
       │  Wi-Fi 6 (2G/5G) │ │ ares_usb_rx      │ │ NVS Encrypted │
       │  BLE 5.0 GAP Obs │ │ ares_proto_task  │ │ ares_sec      │
       │  IEEE 802.15.4   │ │ ares_telemetry   │ │ mbedtls HMAC  │
       └──────────────────┘ └──────────────────┘ └───────────────┘
                                     │
                                     ▼
                        [ USB Serial/JTAG Engine ]
                                     │
                             (ARES/1.0 Wire)
                                     ▼
                        [ ARES FastAPI Backend ]
```

## 1. Subsystem Decomposition
- **Core App (`ares_app.c/h`)**: Central state machine (`BOOTING` -> `INITIALIZING` -> `READY` / `BUSY`).
- **Transport (`ares_transport_usb.c/h`)**: High-speed USB Serial/JTAG line-buffered frame delivery decoupled via FreeRTOS queue.
- **Protocol & Validation (`ares_protocol.c/h`)**: JSON parser, message type whitelist, monotonic sequence checks, clock skew verification, and HMAC-SHA256 signature calculation.
- **Command Engine (`ares_commands.c/h`)**: Whitelist dispatcher for `HELLO`, `DEVICE_INFO`, `CAPABILITIES`, `HEARTBEAT`, `WIFI_SCAN_START/STOP`, `BLE_SCAN_START/STOP`, and `STOP`.
- **Radios (`wifi/`, `ble/`, `ieee802154/`)**: Non-offensive, authorized dual-band discovery observers with SHA-256 MAC anonymization.
