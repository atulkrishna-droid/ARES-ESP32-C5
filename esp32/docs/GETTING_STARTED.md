# ARES ESP32-C5 Firmware — Getting Started Guide

## 1. Prerequisites
- **Target Board**: ESP32-C5-DevKitC-1 (RISC-V 32-bit Single-Core, Dual-Band 2.4/5GHz Wi-Fi 6, BLE, IEEE 802.15.4)
- **Framework**: ESP-IDF v5.3+ (Official Espressif IoT Development Framework)
- **Host System**: Windows, Linux, or macOS with Python 3.10+ and CMake 3.16+
- **USB Cable**: USB Type-C data cable connected to the USB-to-UART / USB Serial-JTAG port.

## 2. Setting Target and Building
From the `esp32/` directory:

```bash
# 1. Set chip target to esp32c5
idf.py set-target esp32c5

# 2. Build the firmware binary
idf.py build
```

The build produces:
- `build/bootloader/bootloader.bin`
- `build/partition_table/partition-table.bin` (using custom 8MB `partitions.csv`)
- `build/ares_esp32_c5_firmware.bin`

## 3. Flashing & Serial Monitor

```bash
# Flash firmware to the connected DevKitC-1
idf.py flash

# Open serial console monitor
idf.py monitor
```

Upon boot, the device logs initialization status and automatically transmits the initial `HELLO` message frame over the USB Serial/JTAG interface:
```json
{"protocol":"ARES/1.0","type":"HELLO","device_id":"ares-esp32-c5-aabbccddeeff","firmware_version":"1.0.0","protocol_version":"ARES/1.0"}
```
