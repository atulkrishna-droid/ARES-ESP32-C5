"""Hardware capability parser and ESP32-C5 profile validator."""
from typing import Any, Dict


class CapabilityParser:
    @staticmethod
    def parse_esp32_c5_devkit(raw_caps: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize hardware capabilities for ESP32-C5-DevKitC-1.
        Enforces strict architectural boundaries:
        - bluetooth_classic is ALWAYS False on ESP32-C5.
        - Wi-Fi is dual-band (2.4GHz + 5GHz) with Wi-Fi 6.
        - SD, GPS, Battery, Display are not assumed built-in.
        """
        chip = raw_caps.get("chip", "ESP32-C5")
        board = raw_caps.get("board", "ESP32-C5-DevKitC-1")
        flash = raw_caps.get("flash", "8MB")
        psram = raw_caps.get("psram", "8MB")

        normalized = {
            "chip": chip,
            "board_name": board,
            "flash_size": flash,
            "psram_size": psram,
            "wifi_24": True,
            "wifi_5": True,
            "wifi6": True,
            "ble": True,
            "bluetooth_classic": False,  # Strict hardware boundary
            "ieee802154": True,
            "zigbee": True,
            "thread": True,
            "usb": True,
            "sd": bool(raw_caps.get("has_sd_module", False)),
            "gps": bool(raw_caps.get("has_gps_module", False)),
            "battery": bool(raw_caps.get("has_battery_subsystem", False)),
            "display": False,
            "touchscreen": False,
            "peripheral_pinouts": {
                "microsd_spi": {
                    "miso": "GPIO2",
                    "mosi": "GPIO7",
                    "sck": "GPIO6",
                    "cs": "GPIO10",
                },
                "uart_debug": {
                    "tx": "GPIO4",
                    "rx": "GPIO5",
                },
            },
        }
        return normalized
