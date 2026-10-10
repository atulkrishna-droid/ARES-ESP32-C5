# ARES Android Agent — Testing & Validation Guide

## 1. Emulator-First Test Strategy

Per Section 14, all Android Agent validation is completed on the **Android Emulator** before physical hardware deployment.

### Emulator Setup Instructions
1. In Android Studio, open **Virtual Device Manager**.
2. Create an Android Virtual Device (AVD):
   - **Hardware Profile:** Pixel 8 Pro
   - **System Image:** Android 14 (API 34) with Google APIs (x86_64)
   - **Network:** Default NAT (maps `10.0.2.2` to host computer localhost)
3. Start the emulator.

---

## 2. End-to-End Validation Workflow

```
Android Emulator               Host Backend (FastAPI)
      │                                  │
      ├─── 1. POST /android/enroll ─────►│ (Enroll Device)
      │                                  │
      ├─── 2. ARES/1.0 HELLO ───────────►│ (Authorize Case)
      │                                  │
      ├─── 3. Ingest Inventory ─────────►│ (Store Apps & Permissions)
      │                                  │
      ├─── 4. Run Assessment ───────────►│ (Evaluate Posture)
      │                                  │
      ├─── 5. EVIDENCE_METADATA ────────►│ (HMAC Audit Ledger)
      │                                  │
      ├─── 6. Simulate Disconnect ──────►│ (Status -> INTERRUPTED)
      │                                  │
      └─── 7. Test Revocation ──────────►│ (State -> REVOKED)
```

---

## 3. Automated Unit Tests

Execute JVM unit tests via Gradle:
```bash
cd android-agent
./gradlew test --info
```

### Covered Test Cases
- `DeviceIdentityTest`: Format verification (`ares-android-xxxxxxxx`), persistence, revocation locks, case scoping.
- `ProtocolEnvelopeTest`: Canonical JSON bytes, signature verification, clock skew rejection.
- `SequenceTrackerTest`: Monotonic outbound counter, replay detection.
- `SecurityPostureEngineTest`: `ANDROID-SEC-001`, `APP-DEBUG-001`, `APP-PERM-001`, `ANDROID-DEV-001`, `NETWORK-SEC-001`.
- `CapabilityDiscoveryTest`: Legitimate framework API queries and mock fallback.
- `ApplicationInventoryTest`: Package scanning and permission classification.
- `EvidenceMetadataTest`: SHA-256 and SHA-512 calculation and schema integrity.
- `StateMachineTest`: State transitions, disconnect recovery, and revocation enforcement.
