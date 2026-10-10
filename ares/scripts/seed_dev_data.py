"""Database seeding script for local development and testing."""
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.database import SessionLocal, init_db
from app.core.security import hash_password
from app.models.case import Case
from app.models.device import Device, DeviceAuthorization
from app.models.esp32_device import ESP32Device
from app.models.hardware_profile import HardwareProfile
from app.models.user import Permission, Role, User
from app.services.audit_service import AuditService


def seed_all():
    print("[*] Initializing database tables...")
    init_db()
    db = SessionLocal()

    try:
        print("[*] Seeding permissions & roles...")
        all_perms = [
            ("user.read", "Read user profiles", "USER"),
            ("user.write", "Modify user accounts", "USER"),
            ("case.read", "View cases", "CASE"),
            ("case.write", "Create and edit cases", "CASE"),
            ("device.read", "View devices", "DEVICE"),
            ("device.enroll", "Enroll new hardware", "DEVICE"),
            ("device.authorize", "Authorize devices for cases", "DEVICE"),
            ("device.revoke", "Revoke device access", "DEVICE"),
            ("assessment.create", "Create assessments", "ASSESSMENT"),
            ("assessment.start", "Execute assessments", "ASSESSMENT"),
            ("assessment.stop", "Halt assessments", "ASSESSMENT"),
            ("assessment.read", "Read assessment findings", "ASSESSMENT"),
            ("assessment.write", "Update assessment findings", "ASSESSMENT"),
            ("esp32.read", "Read ESP32 state and telemetry", "ESP32"),
            ("esp32.connect", "Pair and manage ESP32", "ESP32"),
            ("esp32.scan", "Initiate Wi-Fi and BLE scans", "ESP32"),
            ("evidence.create", "Ingest forensic evidence", "EVIDENCE"),
            ("evidence.read", "Read forensic evidence", "EVIDENCE"),
            ("report.generate", "Generate assessment reports", "REPORT"),
            ("report.read", "Read assessment reports", "REPORT"),
            ("audit.read", "View and verify audit ledger", "AUDIT"),
            ("lab.execute", "Run laboratory simulations", "LAB"),
            ("*", "Full administrative privilege", "ADMIN"),
        ]

        perm_map = {}
        for code, desc, cat in all_perms:
            p = db.query(Permission).filter(Permission.name == code).first()
            if not p:
                p = Permission(name=code, description=desc, category=cat)
                db.add(p)
                db.flush()
            perm_map[code] = p

        # Roles
        roles_to_create = {
            "ADMIN": [perm_map["*"]],
            "ANALYST": [
                perm_map["case.read"], perm_map["case.write"],
                perm_map["device.read"], perm_map["device.enroll"], perm_map["device.authorize"],
                perm_map["assessment.create"], perm_map["assessment.start"], perm_map["assessment.stop"],
                perm_map["assessment.read"], perm_map["assessment.write"],
                perm_map["esp32.read"], perm_map["esp32.connect"], perm_map["esp32.scan"],
                perm_map["evidence.create"], perm_map["evidence.read"],
                perm_map["report.generate"], perm_map["report.read"],
                perm_map["audit.read"], perm_map["lab.execute"],
            ],
            "LAB_USER": [
                perm_map["lab.execute"], perm_map["case.read"],
                perm_map["device.read"], perm_map["esp32.read"],
                perm_map["assessment.read"], perm_map["report.read"],
            ],
            "VIEWER": [
                perm_map["case.read"], perm_map["device.read"],
                perm_map["assessment.read"], perm_map["report.read"],
                perm_map["audit.read"],
            ],
        }

        role_map = {}
        for r_name, p_list in roles_to_create.items():
            r = db.query(Role).filter(Role.name == r_name).first()
            if not r:
                r = Role(name=r_name, description=f"{r_name} role")
                r.permissions = p_list
                db.add(r)
                db.flush()
            role_map[r_name] = r

        print("[*] Seeding default users...")
        users = [
            ("admin@ares.internal", "admin", "AdminSecret123!", "Lead Security Admin", "ADMIN"),
            ("analyst@ares.internal", "analyst", "AnalystSecret123!", "Senior Security Analyst", "ANALYST"),
            ("lab@ares.internal", "labuser", "LabSecret123!", "Lab Researcher", "LAB_USER"),
            ("viewer@ares.internal", "viewer", "ViewerSecret123!", "Audit Viewer", "VIEWER"),
        ]

        admin_user = None
        for email, username, pwd, display, role_name in users:
            u = db.query(User).filter(User.username == username).first()
            if not u:
                u = User(
                    email=email,
                    username=username,
                    password_hash=hash_password(pwd),
                    display_name=display,
                    is_active=True,
                    is_verified=True,
                )
                u.roles.append(role_map[role_name])
                db.add(u)
                db.flush()
            if username == "admin":
                admin_user = u

        print("[*] Seeding ESP32-C5 Hardware Profile...")
        c5_profile = db.query(HardwareProfile).filter(HardwareProfile.board_name == "ESP32-C5-DevKitC-1").first()
        if not c5_profile:
            c5_profile = HardwareProfile(
                name="ESP32-C5 DevKitC-1 Standard",
                chip="ESP32-C5",
                board_name="ESP32-C5-DevKitC-1",
                flash_size="8MB",
                psram_size="8MB",
                wifi_24=True,
                wifi_5=True,
                wifi6=True,
                ble=True,
                bluetooth_classic=False,  # Strict ESP32-C5 hardware boundary
                ieee802154=True,
                zigbee=True,
                thread=True,
                usb=True,
                sd=False,                 # External add-on
                gps=False,
                peripheral_pinouts={
                    "microsd_spi": {
                        "miso": "GPIO2",
                        "mosi": "GPIO7",
                        "sck": "GPIO6",
                        "cs": "GPIO10",
                    }
                },
            )
            db.add(c5_profile)
            db.flush()

        print("[*] Seeding default case...")
        test_case = db.query(Case).filter(Case.case_number == "CASE-2026-000001").first()
        if not test_case and admin_user:
            test_case = Case(
                case_number="CASE-2026-000001",
                title="Baseline Wireless & Mobile Security Assessment",
                description="Initial verification and baseline security evaluation for lab assets.",
                created_by=admin_user.id,
                status="OPEN",
                priority="HIGH",
            )
            db.add(test_case)
            db.flush()

        print("[*] Seeding devices and authorizations...")
        esp_dev = db.query(Device).filter(Device.device_uuid == "ESP32-C5-DEVKIT-LAB-001").first()
        if not esp_dev:
            esp_dev = Device(
                device_uuid="ESP32-C5-DEVKIT-LAB-001",
                device_type="ESP32",
                manufacturer="Espressif",
                model="ESP32-C5-DevKitC-1",
                platform="ESP_IDF",
                platform_version="v5.3",
                owner_label="Lab Peripheral #1",
                authorization_status="ACTIVE",
                operational_status="READY",
            )
            db.add(esp_dev)
            db.flush()

            esp_spec = ESP32Device(
                device_id=esp_dev.id,
                hardware_profile_id=c5_profile.id,
                chip="ESP32-C5",
                board_name="ESP32-C5-DevKitC-1",
                board_revision="v1.0",
                flash_size="8MB",
                psram_size="8MB",
                status="READY",
                latest_telemetry={"free_heap": 312000, "free_psram": 7900000, "wifi_state": "IDLE"},
            )
            db.add(esp_spec)

            if test_case and admin_user:
                auth = DeviceAuthorization(
                    device_id=esp_dev.id,
                    case_id=test_case.id,
                    authorized_by=admin_user.id,
                    authorization_method="ADMIN_APPROVAL",
                    scope={"allowed_operations": ["*"]},
                    status="ACTIVE",
                )
                db.add(auth)

        db.commit()
        print("[+] Seed completed successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
