"""Laboratory Mode and Synthetic Security Scenarios.

Provides strictly isolated educational demonstrations and testing environments
using synthetic data and simulated devices.
"""
from typing import Any, Dict, List


class LabSimulator:
    @staticmethod
    def get_available_scenarios() -> List[Dict[str, Any]]:
        return [
            {
                "scenario_id": "LAB-SCENARIO-001",
                "title": "Mobile Application Security & Permission Analysis",
                "category": "APPLICATION_SECURITY",
                "description": "Examines an Android device with a synthetic banking app and a malicious debuggable flashlight tool.",
                "synthetic_devices": ["LAB-ANDROID-001"],
                "learning_objectives": [
                    "Detect debuggable application flags in manifests",
                    "Identify excessive background location and accessibility permissions",
                    "Understand mitigation using least privilege architecture",
                ],
            },
            {
                "scenario_id": "LAB-SCENARIO-002",
                "title": "Dual-Band Wi-Fi 6 Security Posture Assessment",
                "category": "WIRELESS",
                "description": "Simulates an ESP32-C5 dual-band survey observing enterprise WPA3 alongside legacy rogue access points.",
                "synthetic_devices": ["LAB-ESP32-001", "LAB-ROUTER-001"],
                "learning_objectives": [
                    "Compare 2.4 GHz vs 5 GHz spectral observations",
                    "Detect unencrypted open hotspots and deprecated WEP configurations",
                    "Document evidence with SHA-256 integrity hashing",
                ],
            },
            {
                "scenario_id": "LAB-SCENARIO-003",
                "title": "Bluetooth Low Energy Peripheral Reconnaissance",
                "category": "BLE_DISCOVERY",
                "description": "Demonstrates passive BLE advertisement observation and service UUID mapping using synthetic beacons.",
                "synthetic_devices": ["LAB-ESP32-001"],
                "learning_objectives": [
                    "Map 16-bit and 128-bit BLE service UUIDs",
                    "Hash hardware MAC addresses for analyst privacy preservation",
                    "Audit nearby unauthenticated telemetry beacons",
                ],
            },
        ]

    @staticmethod
    def get_synthetic_dataset(scenario_id: str) -> Dict[str, Any]:
        if scenario_id == "LAB-SCENARIO-001":
            return {
                "scenario_id": scenario_id,
                "device": {
                    "device_uuid": "LAB-ANDROID-001",
                    "model": "ARES Lab Virtual Android",
                    "android_version": "14",
                    "sdk_version": 34,
                    "usb_debugging": True,
                },
                "applications": [
                    {
                        "package_name": "com.ares.lab.banking",
                        "app_name": "Lab Banking Demo",
                        "debuggable": False,
                        "permissions": ["android.permission.INTERNET"],
                    },
                    {
                        "package_name": "com.ares.lab.flashlight",
                        "app_name": "Lab Super Flashlight",
                        "debuggable": True,  # Triggers APP-DEBUG-001
                        "permissions": [
                            "android.permission.CAMERA",
                            "android.permission.ACCESS_FINE_LOCATION",
                            "android.permission.READ_SMS",  # Triggers APP-PERM-001
                        ],
                    },
                ],
            }
        else:
            return {
                "scenario_id": scenario_id,
                "device": {
                    "device_uuid": "LAB-ESP32-001",
                    "model": "ESP32-C5-DevKitC-1-Lab",
                    "chip": "ESP32-C5",
                },
                "wireless_observations": [
                    {"ssid": "CORP-WPA3-5G", "band": "5GHz", "security": "WPA3-SAE", "channel": 36},
                    {"ssid": "INSECURE-GUEST-2G", "band": "2.4GHz", "security": "OPEN", "channel": 6},
                ],
            }
