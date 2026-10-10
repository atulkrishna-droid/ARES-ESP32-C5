# ARES — Authorized Reconnaissance, Evidence & Security Assessment Platform

> **ARES** is a professional cybersecurity laboratory, authorized mobile-security assessment, digital-forensics evidence management, and ESP32-C5 hardware controller platform.

---

## 1. What ARES Is and What It Is Not

### What ARES Is
- **Authorized Assessment Platform**: Orchestrates verified security evaluations for devices and wireless environments with explicit operational scopes.
- **Hardware Telemetry Peripheral**: Controls dedicated ESP32-C5 hardware (and software simulators) for dual-band 2.4 GHz and 5 GHz Wi-Fi 6 and BLE discovery.
- **Mobile Security Posture Auditor**: Interfaces with authorized Android companion agents to audit developer flags, system patch levels, and application permission privilege.
- **Digital Forensics Evidence System**: Records evidence with SHA-256 integrity hashes and unbroken, tamper-evident cryptographic chain-of-custody tracking.
- **Tamper-Evident Audit Ledger**: Employs mathematical hash-chaining to detect any alteration of historical security logs.

### What ARES Is NOT
- **Not Spyware / Stalkerware**: Contains no covert background surveillance, SMS interception, keylogging, or clandestine phone-monitoring capabilities.
- **Not a Bypass Tool**: Does not bypass Android lock screens, crack PINs, or exploit third-party sandboxes.
- **Not a Deauthentication / Jamming Weapon**: Does not perform wireless deauthentication attacks, frame injection, or network disruption.
- **Not Marauder v8 Firmware**: The ESP32-C5 DevKitC-1 target operates on custom ARES/1.0 firmware protocols with dedicated 8MB partition configurations, separate from commercial v8 consumer boards.

---

## 2. Hardware Architecture: ESP32-C5-DevKitC-1

The primary wireless assessment peripheral is the **ESP32-C5-DevKitC-1** (N8R8 memory variant: 8MB Flash, 8MB PSRAM).

### Hardware Capabilities Database
| Feature | Supported Status | Details |
|---|---|---|
| **2.4 GHz Wi-Fi** | **Yes** | 802.11b/g/n/ax |
| **5 GHz Wi-Fi** | **Yes** | 802.11a/n/ac/ax (Wi-Fi 6) |
| **Bluetooth Low Energy** | **Yes** | BLE 5.0 (Passive advertisement observation) |
| **Bluetooth Classic** | **NO** | `bluetooth_classic = False` strictly enforced |
| **IEEE 802.15.4** | **Yes** | Zigbee / Thread capable |
| **USB Communication** | **Yes** | USB-CDC serial transport for ARES/1.0 |
| **MicroSD SPI Module** | **Optional Add-on** | `MISO: GPIO2`, `MOSI: GPIO7`, `SCK: GPIO6`, `CS: GPIO10` |
| **Partition Layout** | **Strict 8MB** | `default_8MB` (Prevents cross-flashing incompatible binaries) |

---

## 3. Technology Stack

- **Backend Runtime**: Python 3.12+ / FastAPI / Uvicorn
- **ORM & Migrations**: SQLAlchemy 2.0 / Alembic
- **Validation**: Pydantic v2
- **Database**: PostgreSQL 16 (or SQLite for local dev/testing)
- **Cryptography**: PBKDF2-HMAC-SHA256, PyJWT (HMAC-SHA256), SHA-256/SHA-512 evidence hashing
- **Testing**: Pytest with automated unit, integration, and negative boundary suites
- **Containers**: Docker & Docker Compose

---

## 4. Setup & Running Locally

### Prerequisites
- Python 3.12+ installed
- Virtual environment tool

### Step 1: Create Virtual Environment and Install
```powershell
python -m venv venv
.\venv\Scripts\pip install -r ares\backend\requirements.txt
```

### Step 2: Initialize Database & Seed Baseline Data
```powershell
.\venv\Scripts\python ares\scripts\seed_dev_data.py
```
This prepares:
- Pre-configured Admin, Analyst, Lab User, and Viewer roles with granular RBAC.
- Hardware Profile for `ESP32-C5-DevKitC-1`.
- Baseline Case `CASE-2026-000001`.

### Step 3: Run the Backend Server
```powershell
.\venv\Scripts\uvicorn app.main:app --app-dir ares\backend --reload --port 8000
```
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- Alternative ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/api/v1/openapi.json`

---

## 5. Running Automated Tests

```powershell
cd ares\backend
..\..\venv\Scripts\pytest -v
```

---

## 6. Running the ESP32 Hardware Simulator

You can test full dual-band wireless scans, telemetry, and capabilities without physical hardware using the CLI simulator:
```powershell
.\venv\Scripts\python ares\scripts\run_simulator.py
```
