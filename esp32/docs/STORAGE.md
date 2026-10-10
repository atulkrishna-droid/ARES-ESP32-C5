# ARES Storage Subsystem (Flash & Modular MicroSD)

## 1. Onboard SPI Flash (8MB)
The physical ESP32-C5-DevKitC-1 provides an onboard 8MB quad SPI flash configured as follows:
- `nvs` (24 KB): Boot and system operational state.
- `otadata` (8 KB): Active OTA partition selection.
- `phy_init` (4 KB): Radio RF calibration data.
- `ota_0` (3.5 MB): Primary application firmware image.
- `ota_1` (3.5 MB): Secondary OTA application firmware image.
- `storage` (768 KB): Internal FAT filesystem.
- `ares_sec` (128 KB): Cryptographically isolated secure storage partition.

## 2. Modular MicroSD Support
- External microSD breakout modules (connected via SPI) are **OPTIONAL**.
- If no card is detected, the device operates normally with `storage_state = NOT_PRESENT` and `sd = false`.
- Never claim built-in SD support on the DevKitC-1.
