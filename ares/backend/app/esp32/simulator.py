"""ESP32-C5 Hardware Simulator.

Implements the exact ARES/1.0 protocol in software to enable full end-to-end
testing and development without physical ESP32-C5 hardware.
"""
import random
import time
from typing import Any, Dict, List, Optional
from app.esp32.protocol import AresProtocol
from app.core.security import sha256_hash


class ESP32Simulator:
    def __init__(
        self,
        device_uuid: str = "ESP32-C5-DEVKIT-SIM-001",
        signing_key: Optional[str] = None,
        device_id: Optional[str] = None,
        environment: Optional[str] = None,
        **kwargs,
    ):
        self.device_uuid = device_id or device_uuid
        self.signing_key = signing_key
        self.environment = environment or "SIMULATOR"
        self.sequence = 1
        self.state = "READY"
        self.start_time = time.time()

    @property
    def device_id(self) -> str:
        return self.device_uuid


    def _next_seq(self) -> int:
        seq = self.sequence
        self.sequence += 1
        return seq

    def send_hello(self) -> Dict[str, Any]:
        return self.respond_hello()

    def send_capabilities(self) -> Dict[str, Any]:
        return self.respond_capabilities()

    def handle_command(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming command and return protocol response."""
        command = envelope.get("type")
        payload = envelope.get("payload", {})

        if command == "HELLO":
            return self.respond_hello()
        elif command == "GET_CAPABILITIES" or command == "CAPABILITIES":
            return self.respond_capabilities()
        elif command == "WIFI_SCAN_START":
            band = payload.get("band", "ALL")
            return self.simulate_wifi_scan(band=band)
        elif command == "BLE_SCAN_START":
            return self.simulate_ble_scan()
        elif command == "GET_STATUS" or command == "TELEMETRY":
            return self.respond_telemetry()
        elif command == "STOP":
            self.state = "READY"
            return AresProtocol.create_message(
                message_type="STOP",
                device_id=self.device_uuid,
                payload={"status": "STOPPED", "state": self.state},
                sequence=self._next_seq(),
                signing_key=self.signing_key,
            )
        else:
            return AresProtocol.create_message(
                message_type="ERROR",
                device_id=self.device_uuid,
                payload={"error": f"Unhandled simulator command: {command}"},
                sequence=self._next_seq(),
                signing_key=self.signing_key,
            )

    def respond_hello(self) -> Dict[str, Any]:
        return AresProtocol.create_message(
            message_type="HELLO",
            device_id=self.device_uuid,
            payload={
                "chip": "ESP32-C5",
                "board": "ESP32-C5-DevKitC-1",
                "firmware_version": "1.0.0-sim",
                "protocol": "ARES/1.0",
                "status": self.state,
            },
            sequence=self._next_seq(),
            signing_key=self.signing_key,
        )

    def respond_capabilities(self) -> Dict[str, Any]:
        return AresProtocol.create_message(
            message_type="CAPABILITIES",
            device_id=self.device_uuid,
            payload={
                "chip": "ESP32-C5",
                "board": "ESP32-C5-DevKitC-1",
                "flash": "8MB",
                "psram": "8MB",
                "wifi_24": True,
                "wifi_5": True,
                "wifi6": True,
                "ble": True,
                "bluetooth_classic": False,
                "ieee802154": True,
                "zigbee": True,
                "thread": True,
                "usb": True,
                "sd": False,
                "gps": False,
            },
            sequence=self._next_seq(),
            signing_key=self.signing_key,
        )

    def respond_telemetry(self) -> Dict[str, Any]:
        uptime = int(time.time() - self.start_time)
        return AresProtocol.create_message(
            message_type="TELEMETRY",
            device_id=self.device_uuid,
            payload={
                "uptime_seconds": uptime,
                "free_heap": random.randint(280000, 320000),
                "free_psram": random.randint(7500000, 8000000),
                "wifi_state": "IDLE" if self.state == "READY" else "SCANNING",
                "ble_state": "IDLE",
                "sd_state": "NOT_INSTALLED",
                "usb_state": "CONNECTED",
                "temperature_c": round(random.uniform(38.0, 44.5), 1),
                "power_source": "USB",
                "rssi": -42,
            },
            sequence=self._next_seq(),
            signing_key=self.signing_key,
        )

    def simulate_wifi_scan(self, band: str = "ALL", dwell_time_ms: int = 100) -> Dict[str, Any]:
        """Generate realistic dual-band (2.4GHz + 5GHz) Wi-Fi access point observations."""
        ap_list = [
            # 2.4 GHz BSSIDs
            {
                "ssid": "LAB-INTERNAL-WIFI",
                "bssid": "30:c6:f7:12:34:56",
                "bssid_hash": sha256_hash("30:c6:f7:12:34:56"),
                "channel": 6,
                "frequency": 2437,
                "band": "2.4GHz",
                "rssi": -48,
                "security_type": "WPA2/WPA3",
                "vendor": "Espressif Systems",
            },
            {
                "ssid": "LAB-GUEST-OPEN",
                "bssid": "30:c6:f7:12:34:57",
                "bssid_hash": sha256_hash("30:c6:f7:12:34:57"),
                "channel": 1,
                "frequency": 2412,
                "band": "2.4GHz",
                "rssi": -65,
                "security_type": "OPEN",  # Triggers WIFI-SEC-001 finding
                "vendor": "Espressif Systems",
            },
            # 5 GHz (Wi-Fi 6) BSSIDs
            {
                "ssid": "LAB-HIGH-THROUGHPUT-5G",
                "bssid": "30:c6:f7:55:aa:01",
                "bssid_hash": sha256_hash("30:c6:f7:55:aa:01"),
                "channel": 36,
                "frequency": 5180,
                "band": "5GHz",
                "rssi": -52,
                "security_type": "WPA3-SAE",
                "vendor": "Cisco",
            },
            {
                "ssid": "LEGACY-OFFICE-WEP",
                "bssid": "00:14:22:98:76:54",
                "bssid_hash": sha256_hash("00:14:22:98:76:54"),
                "channel": 40,
                "frequency": 5200,
                "band": "5GHz",
                "rssi": -78,
                "security_type": "WEP",   # Triggers WIFI-SEC-001 finding
                "vendor": "Dell",
            },
        ]

        if band == "2.4GHz":
            ap_list = [a for a in ap_list if a["band"] == "2.4GHz"]
        elif band == "5GHz":
            ap_list = [a for a in ap_list if a["band"] == "5GHz"]

        return AresProtocol.create_message(
            message_type="WIFI_SCAN_RESULT",
            device_id=self.device_uuid,
            payload={"networks": ap_list, "total_observed": len(ap_list)},
            sequence=self._next_seq(),
            signing_key=self.signing_key,
        )

    def simulate_ble_scan(self) -> Dict[str, Any]:
        """Generate realistic Bluetooth Low Energy discovery observations."""
        ble_list = [
            {
                "device_address": "dc:a6:32:11:22:33",
                "name": "ARES-LAB-BEACON",
                "rssi": -55,
                "manufacturer_id": "0x004c",
                "manufacturer_data_hex": "0215e2c56db5dffb48d2b060d0f5a71096e000000000c5",
                "service_uuids": ["0000feaa-0000-1000-8000-00805f9b34fb"],
            },
            {
                "device_address": "e4:5f:01:44:55:66",
                "name": "SMART-SENSOR-C5",
                "rssi": -72,
                "manufacturer_id": "0x02e5",
                "manufacturer_data_hex": "0102030405",
                "service_uuids": ["180d"],  # Heart Rate Service
            },
        ]
        return AresProtocol.create_message(
            message_type="BLE_SCAN_RESULT",
            device_id=self.device_uuid,
            payload={"devices": ble_list, "total_observed": len(ble_list)},
            sequence=self._next_seq(),
            signing_key=self.signing_key,
        )


ESP32C5Simulator = ESP32Simulator
