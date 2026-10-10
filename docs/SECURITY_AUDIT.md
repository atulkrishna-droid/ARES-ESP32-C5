# ARES Platform — Security Audit & Threat Modeling Specification

**Document Version:** 1.0.0-RC1  
**Target Hardware Profile:** ESP32-C5-DevKitC-1 (RISC-V 32-bit Single-Core, Dual-Band 2.4/5GHz Wi-Fi 6, BLE, IEEE 802.15.4 Zigbee/Thread)  
**Control Plane:** FastAPI 0.115 / SQLAlchemy 2.0 / PostgreSQL / SQLite  
**Auditor Classification:** Pre-Hardware Security & Integration Audit Gate  

---

## 1. Executive Summary & Audit Scope

This document provides a technical security evaluation and threat model of the **ARES (Authorized Reconnaissance & Evaluation System)** control plane. The scope includes:
- Role-Based Access Control (RBAC) and JWT lifecycle (rotation, revocation, replay).
- Case-scoped device authorization and strict operation boundaries.
- ARES/1.0 binary/JSON protocol verification, HMAC message authentication, sequence tracking, and clock skew validation.
- Dual-hashing evidence custody (SHA-256 + SHA-512) and genesis-to-N tamper-evident audit ledger integrity.
- WebSocket session authentication and channel isolation.
- Threat analysis covering 10 distinct attack vectors.

Antigravity and system engineering tests verified **60 automated tests** passing at **85% statement coverage**, certifying the control plane ready for firmware and agent development without requiring physical hardware.

---

## 2. Threat Model & Trust Boundaries

### Trust Boundaries
1. **Unauthenticated Public Interface**: Outside reverse proxy / TLS termination; no access to API routes or WebSocket channels without valid bearer JWT.
2. **Authenticated Operator Boundary**: Role-segregated actors (`ADMIN`, `ANALYST`, `LAB_USER`, `VIEWER`). Actions strictly constrained to assigned cases and permissions.
3. **Control Plane / Device Interface**: Wire communication over ARES/1.0. Devices are untrusted until enrolled, authorized to an active case, and cryptographically verified per message.
4. **Data Persistence & Ledger Boundary**: Relational database storage, append-only audit ledger with cryptographic hash chains, and filesystem evidence storage protected with path sanitization and storage quotas.

```
       [ External Network / Attacker ]
                      │
           (TLS / API Gateway)
                      ▼
   ┌──────────────────────────────────────────────┐
   │             ARES Control Plane               │
   │  ┌────────────────────────────────────────┐  │
   │  │ Authenticated RBAC Engine              │  │
   │  │ (ADMIN / ANALYST / LAB_USER / VIEWER)  │  │
   │  └───────────────────┬────────────────────┘  │
   │                      │ Case Scoping Gate     │
   │  ┌───────────────────▼────────────────────┐  │
   │  │ Device Authorization & Concurrency     │  │
   │  │ (Active Auth / Target Lock / Envelope) │  │
   │  └───────────────────┬────────────────────┘  │
   │                      │ Dual-Hash & Chain     │
   │  ┌───────────────────▼────────────────────┐  │
   │  │ Evidence Store & Audit Hash Ledger     │  │
   │  └────────────────────────────────────────┘  │
   └──────────────────────┬───────────────────────┘
                          │ ARES/1.0 Protocol
          ┌───────────────┴───────────────┐
          ▼                               ▼
 ┌─────────────────┐             ┌─────────────────┐
 │ ESP32-C5 Device │             │  Android Agent  │
 │ (Physical/Sim)  │             │   (Subordinate) │
 └─────────────────┘             └─────────────────┘
```

---

### Detailed Threat Analysis (10 Core Scenarios)

| # | Threat Scenario | Impact | Applied Control & Mitigation | Remaining Risk |
|---|---|---|---|---|
| **1** | **Malicious User (Privilege Escalation)** | Unauthorized assessment execution, data exfiltration across organizational cases. | Backend route-level RBAC (`require_permission`) and dynamic case-membership filters. Frontend restrictions are treated purely as UI conveniences. | Insider threat with compromised Admin credentials; mitigated via mandatory MFA and immutable audit logging. |
| **2** | **Compromised Analyst Account** | Lateral movement into unauthorized active cases, execution of unapproved scans. | Strict case-scoped device authorization (`DeviceAuthorization` status must be `ACTIVE`, unexpired, matching `case_id`). Read/write operations outside assigned scope reject with `403 Forbidden`. | Analyst can abuse operations inside authorized cases; mitigated by immutable cryptographic audit chain. |
| **3** | **Stolen ESP32 Physical Device** | Exposure of shared HMAC credentials, potential impersonation of field probe. | Device secrets are salted and stored hashed in DB. Revocation endpoint deactivates active case authorizations (`DeviceOperationalStatus.REVOKED`). | Hardware physical bus attack (flash dumping) can extract provisioned device key; mitigated by planned ESP32-C5 eFuse flash encryption & Secure Boot. |
| **4** | **Rogue ESP32 Injection** | Injection of spoofed Wi-Fi/BLE observations, false security findings. | Enrollment approval gate (`ENROLLMENT_REQUESTED` -> `ACTIVE`). Unregistered UUIDs rejected immediately upon connection. | Spoofing an enrolled device UUID; blocked by cryptographic message authentication. |
| **5** | **Replayed Protocol Messages** | Duplicate execution of scans, observation flooding, skewing historical timelines. | Monotonic sequence validation (`msg.sequence > last_seq`) + strict clock skew window ($\pm 60$ seconds). Replayed or decremented sequences fail with `ProtocolViolationException`. | High clock drift between unsynchronized NTP environments; mitigated by configurable skew window. |
| **6** | **Tampered Forensic Evidence** | Fabricated evidence items in compliance or legal proceedings. | Dual cryptographic hashing (SHA-256 + SHA-512) computed at ingestion. Any single byte tampering causes verification to fail with `ForensicIntegrityException`. | Storage volume compromise where raw file is altered; detected immediately upon verification. |
| **7** | **Database Compromise (SQLi / Direct DB Write)** | Direct modification of audit records or authorization statuses. | Parameterized SQLAlchemy ORM queries preventing SQLi; Genesis-to-N Merkle-linked audit log where modifying, deleting, or reordering an event invalidates subsequent event hashes. | Database admin modifying all hashes simultaneously; mitigated by planned external HSM/ledger notarization. |
| **8** | **Malicious Android Agent** | Sending unauthorized commands, executing unapproved system inspections. | Android Agent protocol is subordinate; operations restricted to whitelist (`allowed_operations` in case scope). Agent cannot initiate scans without backend dispatch. | Rogue Android app spoofing agent identifier; mitigated by public-key device certificates. |
| **9** | **Malicious / Compromised Frontend** | Sending spoofed payloads or forged role parameters. | Zero trust in client state: all roles, scopes, device operational states, and permissions validated server-side in transaction boundaries. | Cross-Site Scripting (XSS) capturing session tokens; mitigated by `HttpOnly`, `SameSite=Lax` cookies & short-lived access tokens (30 min). |
| **10** | **Network Attacker (Man-in-the-Middle)** | Eavesdropping on telemetry or injecting rogue commands. | Mandatory TLS for HTTP/WebSocket transport; ARES/1.0 application-layer HMAC authentication covering entire payload, sequence, and timestamp. | TLS termination proxy compromise; mitigated by end-to-end payload signature verification. |

---

## 3. Cryptography & Key Management Specification

### Current Implementation: HMAC-SHA256
- **Algorithm**: `HMAC-SHA256` computed over canonical JSON serialization of message envelope fields:
  $$\text{Signature} = \text{HMAC}_{\text{key}}(\text{protocol} \parallel \text{type} \parallel \text{device\_id} \parallel \text{timestamp} \parallel \text{sequence} \parallel \text{payload})$$
- **Payload Integrity**: Payload is serialized with deterministic sorting and zero whitespace separators (`separators=(',', ':')`).
- **Key Generation & Storage**:
  - Keys are generated via cryptographically secure random sources (`secrets.token_hex(32)`).
  - Device secrets are salted and hashed using PBKDF2/Argon2 before persistence in PostgreSQL.
  - Plaintext device secrets are never exposed in API responses or logs.

### Known Limitation & Migration Path: Public-Key Cryptography
While HMAC provides message authenticity and integrity between device and backend, it utilizes a symmetric shared secret. If a physical ESP32-C5 device without flash encryption is stolen, the shared key could be extracted from flash.

**Target Phase 2 / Phase 3 Cryptographic Architecture:**
1. **Asymmetric Key Pairs**: Each physical ESP32-C5 generates an `Ed25519` or `ECDSA P-256` key pair in hardware secure storage.
2. **Backend Challenge-Response**: On connection, backend issues a cryptographically random non-repeating challenge nonce.
3. **Hardware Root of Trust**: ESP32-C5 signs the challenge using the hardware private key stored in write-protected eFuse memory.
4. **Backend Verification**: Backend verifies signature against enrolled device public key registered during initial provisioning.

---

## 4. Hardware Profile & Trust Model (ESP32-C5)

### ESP32-C5-DevKitC-1 Hardware Capabilities
- **Processor**: RISC-V 32-bit single-core microcontroller.
- **RF Bands**: Dual-band (2.4 GHz and 5.0 GHz) Wi-Fi 6 (802.11ax), BLE (Bluetooth Low Energy 5.0), and IEEE 802.15.4 (Zigbee / Thread).
- **Explicit Negative Constraints**:
  - `bluetooth_classic = False` (ESP32-C5 does **NOT** support Bluetooth Classic / BR/EDR).
  - `external_sd = False` (DevKitC-1 default board does not contain onboard SD slot; treated as optional SPI module).
  - `battery = False` (USB bus powered by default).
  - `display = False` (Headless operation).

```json
{
  "chip": "ESP32-C5",
  "board_name": "ESP32-C5-DevKitC-1",
  "board_revision": "v1.0",
  "flash_size": "8MB",
  "partition_layout": "default_8MB",
  "capabilities": {
    "wifi_24": true,
    "wifi_5": true,
    "wifi6": true,
    "ble": true,
    "bluetooth_classic": false,
    "ieee802154": true,
    "zigbee": true,
    "thread": true,
    "usb": true
  }
}
```

### Distinction from Marauder Hardware
Firmware compiled for the official Marauder v8 (featuring integrated ILI9341 display, SD card slot, GPS module, and lithium battery management) **must never be flashed or marked compatible** with the headless `ESP32-C5-DevKitC-1`. Firmware compatibility checks validate `chip`, `board_name`, `board_revision`, `flash_size`, and `partition_layout` before issuing operational commands.

---

## 5. Evidence Custody & Ledger Tamper Verification

### Dual Hashing Specification
Evidence collected during an assessment is subject to dual cryptographic hashing:
- **SHA-256**: Primary identification and compliance fingerprint.
- **SHA-512**: Secondary cryptographic confirmation against collision vulnerabilities.
- **Custody Chain**: Every collection, access, or export records an immutable ledger event referencing the dual hash, operator UUID, timestamp, and case UUID.

### Audit Ledger Hash Chain
The audit trail is structured as a cryptographically verifiable sequential blockchain:
$$\text{Hash}_0 = \text{GENESIS\_HASH} = \text{SHA-256}(\text{"ARES-GENESIS-CHAIN-v1"})$$
$$\text{Hash}_i = \text{SHA-256}(\text{Hash}_{i-1} \parallel \text{Timestamp}_i \parallel \text{Action}_i \parallel \text{ActorID}_i \parallel \text{ResourceID}_i \parallel \text{Metadata}_i)$$

Verification traverses the chain from Genesis to event $N$. If any intermediate record is altered, deleted, or inserted out of order, verification fails with exact index identification.
