"""Complete Hardware-Independent End-to-End Integration Test (Section 27)."""
import pytest
from app.esp32.simulator import ESP32C5Simulator
from app.esp32.protocol import AresMessageType
from app.assessment.engine import AssessmentEngine
from app.services.auth_service import AuthService
from app.services.case_service import CaseService
from app.services.device_service import DeviceService
from app.services.evidence_service import EvidenceService
from app.services.report_service import ReportService
from app.services.audit_service import AuditService
from app.models.wifi_network import WifiNetwork
from app.schemas.case import CaseCreateRequest
from app.schemas.device import DeviceEnrollRequest, DeviceAuthorizeRequest
from app.schemas.assessment import AssessmentCreateRequest


def test_full_ares_assessment_lifecycle(db_session, seeded_users):
    """
    Test the complete authoritative lifecycle:
    USER LOGIN -> CREATE CASE -> ENROLL ESP32 -> AUTHORIZE ESP32 ->
    CREATE ASSESSMENT -> VERIFY SCOPE -> START ASSESSMENT ->
    SIMULATOR CONNECTS -> ESP32 HELLO -> CAPABILITY EXCHANGE ->
    WIFI SCAN -> RESULTS INGESTION -> ASSESSMENT ENGINE ->
    FINDINGS CREATED -> AUDIT LOG CHAIN -> ASSESSMENT COMPLETED ->
    REPORT GENERATION -> VERIFY AUDIT CHAIN INTEGRITY.
    """
    admin = seeded_users["admin"]

    # 1. USER LOGIN
    login_data = AuthService.login(db_session, admin.email, "AdminPass123!")
    assert login_data.access_token is not None
    access_token = login_data.access_token

    # 2. CREATE CASE
    case = CaseService.create_case(
        db=db_session,
        data=CaseCreateRequest(
            case_number="CASE-E2E-2026-001",
            title="Field Penetration Testing & Posture Audit",
            description="Operational security assessment of 2.4/5GHz environments.",
        ),
        creator_id=admin.id,
    )
    assert case.id is not None
    assert case.case_number == "CASE-E2E-2026-001"

    # 3. ENROLL ESP32-C5 SIMULATOR
    device = DeviceService.enroll_device(
        db=db_session,
        data=DeviceEnrollRequest(
            device_uuid="ESP32-C5-E2E-HW-001",
            device_type="ESP32",
            environment="SIMULATOR",
            firmware_version="1.0.0-rc1",
            hardware_revision="ESP32-C5-DevKitC-1",
        ),
        actor_id=admin.id,
    )
    assert device.environment == "SIMULATOR"
    assert device.authorization_status in ("ENROLLMENT_REQUESTED", "ENROLLED")

    # 4. AUTHORIZE ESP32 FOR THIS CASE
    auth = DeviceService.authorize_device(
        db=db_session,
        device_id=device.id,
        data=DeviceAuthorizeRequest(
            case_id=case.id,
            authorization_method="OPERATOR_ASSERTED",
            scope={"allowed_operations": ["WIFI_DISCOVERY", "BLE_DISCOVERY", "DEVICE_INVENTORY"]},
        ),
        actor_id=admin.id,
    )
    assert auth.status == "ACTIVE"
    assert device.authorization_status == "ACTIVE"

    # 5. CREATE ASSESSMENT
    assessment = AssessmentEngine.create_assessment(
        db=db_session,
        data=AssessmentCreateRequest(
            case_id=case.id,
            target_device_id=device.id,
            assessment_type="WIFI_DISCOVERY",
            scope_json={"allowed_operations": ["WIFI_DISCOVERY", "BLE_DISCOVERY"]},
        ),
        creator_id=admin.id,
    )
    assert assessment.status == "CREATED"

    # 6. START ASSESSMENT (Validates Scope, Expiry, Device Authorization, Concurrency Lock)
    AssessmentEngine.start_assessment(db_session, assessment.id, actor_id=admin.id)
    assert assessment.status == "RUNNING"
    assert assessment.started_at is not None

    # 7. SIMULATOR CONNECTS & SENDS HELLO
    simulator = ESP32C5Simulator(device_id=device.id, environment="SIMULATOR")
    hello_msg = simulator.send_hello()
    assert hello_msg.type == AresMessageType.HELLO.value
    assert hello_msg.device_id == device.id

    # 8. CAPABILITY EXCHANGE (Hardware Profile: 2.4/5GHz, BLE, Zigbee/Thread, NO Classic BT)
    caps_msg = simulator.send_capabilities()
    payload = caps_msg.payload
    assert payload["wifi_24"] is True
    assert payload["wifi_5"] is True
    assert payload["wifi6"] is True
    assert payload["ble"] is True
    assert payload["bluetooth_classic"] is False
    assert payload["ieee802154"] is True

    # 9. WIFI SCAN (Dual-band simulated survey)
    scan_results = simulator.simulate_wifi_scan(dwell_time_ms=100)
    networks = scan_results["payload"]["networks"]
    assert len(networks) > 0

    # Ingest scan results into assessment observation database
    for ap in networks:
        network = WifiNetwork(
            assessment_id=assessment.id,
            ssid=ap["ssid"],
            bssid_hash=ap["bssid_hash"],
            channel=ap["channel"],
            frequency=ap["frequency"],
            band=ap["band"],
            rssi=ap["rssi"],
            security_type=ap["security_type"],
        )
        db_session.add(network)
    db_session.commit()

    # Ingest deliberate insecure AP to test deterministic finding generation
    insecure_ap = WifiNetwork(
        assessment_id=assessment.id,
        ssid="LEGACY-INSECURE-WEP",
        bssid_hash="bssidhashwep01",
        channel=1,
        frequency=2412,
        band="2.4GHz",
        rssi=-42,
        security_type="WEP",
    )
    db_session.add(insecure_ap)
    db_session.commit()

    # 10. ASSESSMENT ENGINE RUNS EVALUATION
    findings = AssessmentEngine.run_evaluation(db_session, assessment.id, actor_id=admin.id)
    assert len(findings) > 0
    rule_ids = {f.rule_id for f in findings}
    assert "WIFI-SEC-001" in rule_ids  # WEP/OPEN Insecurity finding!
    assert assessment.status == "COMPLETED"
    assert assessment.completed_at is not None

    # 11. FORENSIC EVIDENCE COLLECTION
    evidence = EvidenceService.create_evidence(
        db=db_session,
        case_id=case.id,
        assessment_id=assessment.id,
        device_id=device.id,
        file_name="wifi_scan_results.json",
        raw_bytes=b'{"scan_status": "COMPLETED", "networks_found": 5}',
        collected_by=admin.id,
    )
    assert evidence.sha256_hash is not None

    # 12. GENERATE AUDITABLE REPORT
    report = ReportService.generate_report(db_session, assessment.id, generated_by=admin.id)
    assert report.total_findings > 0
    assert report.compliance_score < 100.0

    # 13. VERIFY COMPLETE CRYPTOGRAPHIC AUDIT CHAIN
    audit_verification = AuditService.verify_chain_integrity(db_session)
    assert audit_verification["is_valid"] is True
    assert audit_verification["verified_events"] >= 5
