# ARES Platform Architecture

## Overview
ARES (Authorized Reconnaissance, Evidence & Security Assessment Platform) is structured around a backend-first, defensible security architecture. The platform orchestrates authorized device assessments, dual-band Wi-Fi/BLE reconnaissance via ESP32-C5 peripherals, deterministic policy audits, and tamper-evident forensics logging.

```
                      +-----------------------------+
                      |         React Web UI        |
                      |      (Future Frontend)      |
                      +--------------+--------------+
                                     | HTTPS / WSS
                                     v
                      +-----------------------------+
                      |       FastAPI Gateway       |
                      |        (/api/v1/*)          |
                      +--------------+--------------+
                                     |
              +----------------------+----------------------+
              |                      |                      |
              v                      v                      v
     +-----------------+    +-----------------+    +-----------------+
     |   Assessment    |    |  Device / ESP32 |    |    Evidence     |
     |     Engine      |    |     Manager     |    |    Service      |
     +--------+--------+    +--------+--------+    +--------+--------+
              |                      |                      |
              +----------------------+----------------------+
                                     |
                                     v
                      +-----------------------------+
                      |     PostgreSQL / SQLite     |
                      |   (SQLAlchemy 2.0 Models)   |
                      +--------------+--------------+
                                     |
         +---------------------------+---------------------------+
         |                                                       |
         v                                                       v
+------------------+                                   +-------------------+
| ESP32-C5 Device  |                                   |  Android Agent    |
| (ARES/1.0 Proto) |                                   | (ARES-MOBILE/1.0) |
+------------------+                                   +-------------------+
```

---

## Subsystem Responsibilities

### 1. API & Authentication Gateway (`app/api/v1/`)
- Strict Bearer token JWT validation with rotating refresh tokens.
- Granular Role-Based Access Control (`ADMIN`, `ANALYST`, `LAB_USER`, `VIEWER`).
- Security middleware injecting `X-Request-ID`, `X-Content-Type-Options: nosniff`, and `X-Frame-Options: DENY`.

### 2. ESP32-C5 Subsystem (`app/esp32/`)
- Implements **ARES/1.0** binary/JSON protocol envelope with sequence counters, millisecond timestamp windows, and HMAC signatures.
- Dedicated hardware capabilities profile for **ESP32-C5-DevKitC-1** (`wifi_24 = True`, `wifi_5 = True`, `wifi6 = True`, `ble = True`, `bluetooth_classic = False`, `sd = False` by default).
- Complete software simulator (`ESP32Simulator`) enabling end-to-end development without physical silicon.

### 3. Assessment & Deterministic Rules Engine (`app/assessment/`)
- Pre-flight check guarantees target device has `ACTIVE` authorization under the assigned `Case`.
- Evaluates deterministic security rules without subjective scoring.
- Rules Catalog includes:
  - `ANDROID-DEBUG-001`: USB Debugging audit
  - `APP-DEBUG-001`: Manifest debuggable flag
  - `APP-PERM-001`: Excessive or dangerous permission audit
  - `WIFI-SEC-001`: Open or WEP encrypted access points
  - `PATCH-LEVEL-001`: Platform patch age audit

### 4. Forensics Evidence & Custody (`app/forensics/` & `app/services/evidence_service.py`)
- Evidence payload abstraction: saves raw artifacts to isolated filesystem/S3 buckets outside the database.
- SHA-256 and SHA-512 cryptographic verification.
- Tamper-evident custody ledger tracking `COLLECTED`, `VIEWED`, `EXPORTED`, and `SEALED` events.

### 5. Cryptographic Audit Ledger (`app/services/audit_service.py`)
- Every sensitive operation (`DEVICE_ENROLLED`, `ASSESSMENT_STARTED`, `EVIDENCE_CREATED`, etc.) is recorded with a SHA-256 hash mathematically linked to `previous_event_hash`.
- Verification endpoint (`/api/v1/audit/verify`) traverses the entire audit log to guarantee no entry has been altered, inserted, or purged.
