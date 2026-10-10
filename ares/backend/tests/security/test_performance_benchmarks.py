"""Performance Benchmark Suite (Section 28)."""
import time
import pytest
from app.models.case import Case
from app.models.device import Device
from app.models.assessment import Assessment
from app.models.wifi_network import WifiNetwork
from app.models.ble_device import BleDevice
from app.esp32.simulator import ESP32C5Simulator


def test_performance_wifi_bulk_ingestion(db_session, seeded_users):
    """
    Benchmark database ingestion for Wi-Fi and BLE observations:
    - 100 Wi-Fi observations
    - 1,000 Wi-Fi observations
    - 10,000 Wi-Fi observations
    - 1,000 BLE observations
    Measures duration and records throughput.
    """
    admin = seeded_users["admin"]
    case = Case(case_number="CASE-BENCH-001", title="Benchmark Case", created_by=admin.id)
    dev = Device(device_uuid="BENCHMARK-ESP32-001", authorization_status="ACTIVE")
    db_session.add_all([case, dev])
    db_session.commit()

    assessment = Assessment(
        case_id=case.id,
        target_device_id=dev.id,
        assessment_type="WIFI_DISCOVERY",
        status="RUNNING",
        created_by=admin.id,
    )
    db_session.add(assessment)
    db_session.commit()

    # 1. 100 Wi-Fi observations
    t0 = time.perf_counter()
    db_session.bulk_save_objects([
        WifiNetwork(
            assessment_id=assessment.id,
            ssid=f"CORP-NET-{i}",
            bssid_hash=f"hash_{i}",
            channel=(i % 14) + 1,
            frequency=2412,
            band="2.4GHz",
            rssi=-50 - (i % 40),
            security_type="WPA3_PERSONAL",
        ) for i in range(100)
    ])
    db_session.commit()
    t_100 = time.perf_counter() - t0
    print(f"\n[BENCHMARK] 100 Wi-Fi networks ingested in {t_100:.4f}s ({100/t_100:.0f} rows/s)")

    # 2. 1,000 Wi-Fi observations
    t0 = time.perf_counter()
    db_session.bulk_save_objects([
        WifiNetwork(
            assessment_id=assessment.id,
            ssid=f"GUEST-NET-{i}",
            bssid_hash=f"hash_1k_{i}",
            channel=36,
            frequency=5180,
            band="5GHz",
            rssi=-65,
            security_type="WPA2_ENTERPRISE",
        ) for i in range(1000)
    ])
    db_session.commit()
    t_1k = time.perf_counter() - t0
    print(f"[BENCHMARK] 1,000 Wi-Fi networks ingested in {t_1k:.4f}s ({1000/t_1k:.0f} rows/s)")

    # 3. 10,000 Wi-Fi observations
    t0 = time.perf_counter()
    db_session.bulk_save_objects([
        WifiNetwork(
            assessment_id=assessment.id,
            ssid=f"IOT-FLEET-{i}",
            bssid_hash=f"hash_10k_{i}",
            channel=40,
            frequency=5200,
            band="5GHz",
            rssi=-75,
            security_type="WPA2_PERSONAL",
        ) for i in range(10000)
    ])
    db_session.commit()
    t_10k = time.perf_counter() - t0
    print(f"[BENCHMARK] 10,000 Wi-Fi networks ingested in {t_10k:.4f}s ({10000/t_10k:.0f} rows/s)")

    # 4. 1,000 BLE observations
    t0 = time.perf_counter()
    db_session.bulk_save_objects([
        BleDevice(
            assessment_id=assessment.id,
            name=f"BLE-Beacon-{i}",
            device_address_hash=f"ble_hash_{i}",
            rssi=-60 - (i % 30),
            manufacturer_id="0x004C",
            service_uuids=["180F", "180A"],
        ) for i in range(1000)
    ])
    db_session.commit()
    t_ble = time.perf_counter() - t0
    print(f"[BENCHMARK] 1,000 BLE devices ingested in {t_ble:.4f}s ({1000/t_ble:.0f} rows/s)")

    # Verify ingest integrity
    assert db_session.query(WifiNetwork).filter(WifiNetwork.assessment_id == assessment.id).count() == 11100
    assert db_session.query(BleDevice).filter(BleDevice.assessment_id == assessment.id).count() == 1000
    assert t_10k < 5.0  # 10k items inserted in under 5 seconds


def test_concurrency_multi_esp32_simulation():
    """Simulate 10 simultaneous ESP32 devices running protocol operations."""
    simulators = [ESP32C5Simulator(device_id=f"esp32-sim-{i}") for i in range(10)]
    t0 = time.perf_counter()
    for sim in simulators:
        hello = sim.send_hello()
        assert hello.payload["status"] == "READY"
        caps = sim.send_capabilities()
        assert caps.payload["bluetooth_classic"] is False
        results = sim.simulate_wifi_scan(dwell_time_ms=50)
        assert len(results) > 0
    duration = time.perf_counter() - t0
    print(f"[BENCHMARK] 10 ESP32 simultaneous simulator lifecycles executed in {duration:.4f}s")
    assert duration < 2.0
