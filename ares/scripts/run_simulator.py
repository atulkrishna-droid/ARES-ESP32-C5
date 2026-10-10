"""Standalone CLI runner for the ESP32-C5 Hardware Simulator."""
import json
import os
import sys
import time

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.esp32.protocol import AresProtocol
from app.esp32.simulator import ESP32Simulator


def run_simulator_interactive():
    print("=" * 60)
    print("  ARES ESP32-C5-DevKitC-1 Hardware Simulator CLI")
    print("  Protocol Version: ARES/1.0")
    print("=" * 60)

    sim = ESP32Simulator(device_uuid="ESP32-C5-DEVKIT-SIM-001")
    print(f"[+] Initialized virtual device: {sim.device_uuid}")

    # Send HELLO
    hello_msg = sim.respond_hello()
    print(f"\n[>] OUTGOING HELLO:\n{json.dumps(hello_msg, indent=2)}")

    # Capabilities
    caps_msg = sim.respond_capabilities()
    print(f"\n[>] HARDWARE CAPABILITIES:\n{json.dumps(caps_msg, indent=2)}")

    # Wi-Fi Dual-band Scan
    print("\n[*] Simulating dual-band 2.4 GHz + 5 GHz (Wi-Fi 6) scan...")
    wifi_msg = sim.simulate_wifi_scan(band="ALL")
    print(f"[>] OBSERVED NETWORKS ({len(wifi_msg['payload']['networks'])} APs):\n{json.dumps(wifi_msg, indent=2)}")

    # BLE Discovery
    print("\n[*] Simulating BLE advertisement discovery...")
    ble_msg = sim.simulate_ble_scan()
    print(f"[>] OBSERVED BLE BEACONS ({len(ble_msg['payload']['devices'])} devices):\n{json.dumps(ble_msg, indent=2)}")

    # Telemetry
    print("\n[*] Simulating hardware telemetry snapshot...")
    telem_msg = sim.respond_telemetry()
    print(f"[>] TELEMETRY:\n{json.dumps(telem_msg, indent=2)}")

    print("\n[+] Simulator verification successful. Ready for API ingestion.")


if __name__ == "__main__":
    run_simulator_interactive()
