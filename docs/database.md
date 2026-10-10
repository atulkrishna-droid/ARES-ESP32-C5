# ARES Database Specification

## Relational Schema Overview
The ARES database is built on SQLAlchemy 2.0 and supports PostgreSQL (production) and SQLite (local testing & development). Primary entities use UUID string identifiers, UTC timestamps, foreign key cascade rules, and dedicated indexes.

```
                              +------------------+
                              |      USERS       |
                              +--------+---------+
                                       |
                     +-----------------+-----------------+
                     |                 |                 |
                     v                 v                 v
              +------------+    +------------+    +------------+
              | USER_ROLES |    |   CASES    |    | AUDIT_LOGS |
              +------------+    +------+-----+    +------------+
                                       |
                     +-----------------+-----------------+
                     |                 |                 |
                     v                 v                 v
             +---------------+  +-------------+   +------------+
             | DEVICE_AUTHS  |  | ASSESSMENTS |   |  EVIDENCE  |
             +---------------+  +------+------+   +-----+------+
                                       |                |
                     +-----------------+                v
                     |                 |          +------------+
                     v                 v          |  CUSTODY   |
               +-----------+     +-----------+    +------------+
               |  FINDINGS |     |   WIFI    |
               +-----------+     +-----------+
```

---

## Core Tables & Schema Definitions

### 1. `users`, `roles`, `permissions`
- Granular Role-Based Access Control: `role_permissions` and `user_roles` association tables.
- Passwords hashed using PBKDF2-HMAC-SHA256 (`600,000` iterations, 16-byte cryptographically secure salt).

### 2. `cases`
- Formatted case numbers: `CASE-{YYYY}-{000001}`.
- Statuses: `OPEN`, `IN_PROGRESS`, `PAUSED`, `COMPLETED`, `CLOSED`, `ARCHIVED`.
- Priority: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.

### 3. `devices` & `device_authorizations`
- Lifecycle states: `UNREGISTERED` -> `ENROLLMENT_REQUESTED` -> `PENDING_APPROVAL` -> `AUTHORIZED` -> `ACTIVE` -> `REVOKED`.
- An assessment cannot start unless a device has an `ACTIVE` authorization record tied to the specific case.

### 4. `hardware_profiles` & `esp32_devices`
- Profile metadata explicitly tracks wireless and physical pinout capabilities.
- Enforces `bluetooth_classic = False` for ESP32-C5.
- SPI MicroSD pins: `MISO GPIO2, MOSI GPIO7, SCK GPIO6, CS GPIO10`.
- Partition Layout validation (e.g. `default_8MB`).

### 5. `assessments` & `findings`
- Strictly bounded by `scope_json` (`allowed_operations`).
- Deterministic findings with automated severity classification: `INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.

### 6. `evidence` & `chain_of_custody_events`
- SHA-256 and SHA-512 cryptographic verification.
- Custody ledger mathematically linked to previous custody event hashes.

### 7. `audit_logs`
- Tamper-evident ledger.
- `event_hash = SHA256(previous_event_hash + canonical_json(event_payload))`.
- Cryptographic verification via `GET /api/v1/audit/verify`.
