# ARES Bluetooth Low Energy (BLE) Subsystem

## 1. Physical Architecture
- **Bluetooth Specification**: Bluetooth Low Energy (BLE 5.0) only.
- **CRITICAL HARDWARE CONSTRAINT**: The ESP32-C5 does **NOT** support Bluetooth Classic (BR/EDR). `bluetooth_classic` is explicitly set to `false`.

## 2. Operation Mode
- Passive / Active Observer GAP scanner.
- Collects:
  - `device_name`: Advertised peripheral name
  - `device_address_hash`: First 12 hex digits of SHA-256(MAC)
  - `rssi`: Signal strength in dBm
  - `manufacturer_data`: Raw hex payload (e.g. iBeacon, AltBeacon)
  - `service_uuids`: 16-bit or 128-bit advertised service UUID strings

**Strict Operational Boundary**:
- No unauthorized pairing.
- No GATT connection or credential harvesting.
