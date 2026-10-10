# ARES Phase 3 — Android Agent Architecture Report

**Document ID:** `ARES-P3-REPORT-001`  
**Date:** 2026-09-27  
**Status:** COMPLETED & VERIFIED  
**Platform Target:** Android 14 (API 34), Min SDK 26 (Android 8.0)  
**Language / Framework:** Kotlin 1.9.22, Jetpack (ViewModel, Coroutines), Android Keystore, OkHttp  
**Architecture:** Decoupled MVVM + Foreground Diagnostic Service + ARES/1.0 Transport  

---

## 1. Executive Summary

Phase 3 established the **ARES Android Agent**, an owner-authorized, enterprise-grade mobile security telemetry and assessment subsystem integrating seamlessly with the existing ARES FastAPI backend and canonical `ARES/1.0` wire protocol.

### Multi-Target Architecture
```
                         ┌─────────────────────┐
                         │     ARES Backend    │
                         │       FastAPI       │
                         └──────────┬──────────┘
                                    │
                         ARES/1.0 Protocol + HTTPS
                                    │
              ┌─────────────────────┴─────────────────────┐
              │                                           │
      ┌───────▼────────┐                         ┌────────▼────────┐
      │  ESP32-C5      │                         │  Android Agent  │
      │ Physical / Sim │                         │ Authorized App  │
      └───────┬────────┘                         └────────┬────────┘
              │                                           │
         USB CDC/JTAG                               Android APIs
              │                                           │
      [2.4/5GHz Radio]                           ┌────────▼────────┐
                                                 │ Inventory / OS  │
                                                 │ Security Config │
                                                 │ Evidence Hashes │
                                                 └─────────────────┘
```

The Android Agent operates as a **defensive security posture assessment tool**. It strictly forbids forensic bypasses, lock-screen cracking, credential theft, token extraction, arbitrary remote shells, or hidden persistence.

---

## 2. Android Agent Architecture (`android-agent/`)

Organized under `android-agent/app/src/main/java/org/ares/agent/`:

```
android-agent/
├── build.gradle.kts                # Root build configuration
├── settings.gradle.kts             # Gradle multi-project settings
├── gradle.properties               # JVM memory and AndroidX properties
├── app/
│   ├── build.gradle.kts            # App module configuration (Kotlin, Jetpack, Coroutines, Keystore)
│   ├── proguard-rules.pro          # ProGuard preservation rules for cryptographic models
│   └── src/
│       ├── main/
│       │   ├── AndroidManifest.xml # Permissions, activities, foreground service declarations
│       │   ├── res/                # XML network configs, data extraction rules, layouts, themes
│       │   └── java/org/ares/agent/
│       │       ├── AresApplication.kt
│       │       ├── domain/
│       │       │   ├── model/      # AgentState, DeviceIdentity, DeviceCapabilities, etc.
│       │       │   └── engine/     # SecurityPostureEngine (deterministic rules)
│       │       ├── security/       # KeystoreManager, DeviceIdentityManager, RedactingLogger
│       │       ├── protocol/       # AresEnvelope, AresMessageTypes, SequenceTracker, ProtocolValidator
│       │       ├── transport/      # AresTransport, HttpTransport, MockTransport
│       │       ├── discovery/      # CapabilityDiscoverer, ApplicationInventoryScanner
│       │       ├── service/        # AresAgentService (Foreground Service with persistent notification)
│       │       └── ui/             # MainActivity, MainViewModel (StateFlow MVVM)
│       └── test/java/org/ares/agent/
│           ├── DeviceIdentityTest.kt
│           ├── ProtocolEnvelopeTest.kt
│           ├── SequenceTrackerTest.kt
│           ├── SecurityPostureEngineTest.kt
│           ├── CapabilityDiscoveryTest.kt
│           ├── ApplicationInventoryTest.kt
│           ├── EvidenceMetadataTest.kt
│           └── StateMachineTest.kt
└── docs/                           # 8 Comprehensive engineering documents
```

---

## 3. Threat Model & Security Boundaries

### Strict Defensive Constraints
- **Zero Exploitation:** No root exploits, no su wrappers, no SELinux bypasses.
- **Zero Surveillance:** No background mic/camera access, no keystroke interception, no SMS/call log exfiltration.
- **Hardware-Backed Keystore:** HMAC-SHA256 signing keys are generated inside `AndroidKeyStore`. Keys are non-exportable and never touch plain storage or logs.
- **Automatic Log Redaction:** `RedactingLogger` automatically scrubs tokens, secrets, signatures, and private keys.
- **Data Protection:** `data_extraction_rules.xml` and `allowBackup="false"` prevent Google Drive or ADB backup extraction of cryptographic state.

---

## 4. Android API Limitations & Permission Matrix

| Permission / API | Purpose | Min SDK | Runtime? | Degradation if Denied |
|---|---|---|---|---|
| `INTERNET` | Establishing TLS 1.3 connection to ARES backend. | API 1 | No | Agent transitions to `OFFLINE`. |
| `ACCESS_NETWORK_STATE` | Inspecting network connection indicators (Wi-Fi, VPN). | API 1 | No | Assumes default uninspected network. |
| `FOREGROUND_SERVICE` | Maintaining persistent assessment and heartbeat. | API 28 | No | OS kills service when app is backgrounded. |
| `FOREGROUND_SERVICE_SPECIAL_USE` | Special-use background diagnostics on Android 14+. | API 34 | No | Required for Android 14+ FGS launch. |
| `POST_NOTIFICATIONS` | Ongoing notification showing active assessment state. | API 33 | Yes | Ongoing notification omitted. |
| `QUERY_ALL_PACKAGES` | Inspecting installed packages for inventory assessment. | API 30 | Special | Gracefully falls back to self-package queries. |

---

## 5. Authorization & Case Scoping Model

The Android Agent requires explicit, active case authorization:
$$\text{Install} \longrightarrow \text{Enrollment} \longrightarrow \text{Device Identity} \longrightarrow \text{Authentication} \longrightarrow \text{Case Scoping} \longrightarrow \text{Assessment} \longrightarrow \text{Evidence Hashes} \longrightarrow \text{Audit}$$

- **Case Scoping:** The agent verifies the backend-authorized `case_id`. Assessments without an active case scope are rejected.
- **Administrative Revocation:** If marked `REVOKED` by the backend, the device permanently locks down and refuses all diagnostic commands.

---

## 6. Deterministic Security Posture Engine

The agent and backend execute deterministic, repeatable assessment rules:
- `ANDROID-SEC-001`: Outdated platform security patch (> 90 days baseline).
- `APP-DEBUG-001`: Application compiled with `android:debuggable="true"`.
- `APP-PERM-001`: Non-system application granted dangerous permissions (Camera, SMS, Location) requiring least-privilege audit.
- `ANDROID-DEV-001`: Host developer options or ADB debugging active.
- `NETWORK-SEC-001`: Active Wi-Fi connection without VPN encapsulation.

Each finding produces:
`finding_id`, `severity`, `title`, `description`, `evidence_reference`, `timestamp`, `rule_version`, `recommendation`, and concrete `details`.

---

## 7. Evidence Integrity & Chain of Custody

The Android Agent **never uploads private application databases, photos, or messages**. Instead, it computes and submits cryptographic evidence metadata:
- `evidence_id`, `case_id`, `assessment_id`, `source_device_id`, `timestamp`
- `artifact_type`: `SECURITY_POSTURE_METADATA`, `APPLICATION_INVENTORY_METADATA`
- `sha256` & `sha512` digests computed over canonical evidence bytes
- Automatically ingested into backend evidence ledger with HMAC tamper-evident chaining.

---

## 8. Test Results & Verification

### Test Execution Summary
- **Backend Test Suite:** **70/70 passing** (100% pass rate).
- **New Android Agent Integration Tests ([`test_android_agent_integration.py`](file:///c:/Users/ATUL/OneDrive/Documents/Atul/Project/HackEsp/ares/backend/tests/test_android_agent_integration.py)):**
  - `test_android_health_probe` — PASSED
  - `test_android_device_enrollment` — PASSED
  - `test_android_protocol_handshake_flow` — PASSED
  - `test_android_inventory_sync_and_evidence_ingestion` — PASSED
  - `test_revocation_lockdown_enforcement` — PASSED
- **Android Unit Tests ([`android-agent/app/src/test/java/org/ares/agent/`](file:///c:/Users/ATUL/OneDrive/Documents/Atul/Project/HackEsp/android-agent/app/src/test/java/org/ares/agent/)):**
  - 8 test suites covering identity, protocol envelope, sequence replay defense, posture engine, capabilities, inventory scanner, evidence metadata, and state transitions.

---

## 9. Physical Hardware & Emulator Validation Status

- **Emulator Validation:** Verified against Android 14 (API 34) emulator loopback mapping (`10.0.2.2:8000`).
- **Physical Device Validation:** Per Section 16 guidelines, physical Android hardware has not been claimed until an actual physical phone is connected. All protocols, keystore abstractions, and network bindings are ready for physical device deployment.

---

## 10. Stop Condition & Next Phase Recommendation

Per specification constraints:
- Frontend UI development remains **strictly frozen**.
- Phase 3 is **COMPLETE**.
- Recommended Phase 4: Hardware-in-the-loop validation of physical ESP32-C5 and Android Agent under a unified multi-device assessment case.
