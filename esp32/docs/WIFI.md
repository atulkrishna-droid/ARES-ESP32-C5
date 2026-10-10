# ARES Wi-Fi Subsystem (ESP32-C5 Dual-Band Wi-Fi 6)

## 1. Physical Radio Features
- **Wi-Fi Generation**: Wi-Fi 6 (802.11ax), backwards-compatible with 802.11b/g/n/a/ac.
- **Bands**:
  - **2.4 GHz**: Channels 1–14 (2412–2484 MHz), labeled `"2.4GHz"` (`2G`).
  - **5.0 GHz**: Channels 36–165 (5180–5825 MHz), labeled `"5GHz"` (`5G`).
- **Channel Switching**: Dual-band radio operates across both bands sequentially in scan mode.

## 2. Telemetry Schema
Scan records contain:
- `ssid`: Network name (or empty if hidden)
- `bssid_hash`: First 12 hex digits of SHA-256(BSSID) for anonymized tracking
- `channel`: Primary RF channel
- `frequency`: Center frequency in MHz
- `band`: `"2.4GHz"` or `"5GHz"`
- `rssi`: Received signal strength indicator in dBm
- `security_type`: `"OPEN"`, `"WEP"`, `"WPA"`, `"WPA2"`, `"WPA3"`, `"WPA2_WPA3"`

**Security Rule**: No passwords, PMKID handshakes, or raw keystrokes are ever captured or stored.
