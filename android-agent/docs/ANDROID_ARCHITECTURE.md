# ARES Android Agent — Architecture Specification

## 1. System Overview

The **ARES Android Agent** is an owner-authorized, enterprise-grade mobile security telemetry and assessment component of the ARES platform. It operates strictly within official Android SDK guidelines and security boundaries, communicating via the canonical `ARES/1.0` wire protocol with the FastAPI backend.

```
┌────────────────────────────────────────────────────────┐
│                   ARES Android Agent                   │
├────────────────────────────────────────────────────────┤
│ UI Layer (MainActivity / ViewBinding / Material UI)    │
│   ↓                                                    │
│ ViewModel Layer (MainViewModel / StateFlow)            │
│   ↓                                                    │
│ Domain Layer (SecurityPostureEngine / Data Models)     │
│   ↓                                                    │
│ Service Layer (AresAgentService / Foreground Worker)   │
│   ↓                                                    │
│ Security & Identity (KeystoreManager / Non-Privileged) │
│   ↓                                                    │
│ Protocol & Transport (AresProtocol / HttpTransport)    │
└───────────────────────────┬────────────────────────────┘
                            │ HTTPS / TLS (ARES/1.0)
                            ▼
┌────────────────────────────────────────────────────────┐
│              ARES FastAPI Backend / Database           │
└────────────────────────────────────────────────────────┘
```

---

## 2. Layer Definitions

### UI & Presentation Layer (`org.ares.agent.ui`)
- **`MainActivity`**: Provides direct visibility to the device owner regarding registration status, active case scoping, and deterministic findings.
- **`MainViewModel`**: Exposes immutable `StateFlow` streams from background services to ensure UI remains reactive and decoupled from background tasks.

### Domain Layer (`org.ares.agent.domain`)
- **`SecurityPostureEngine`**: Evaluates platform security configuration and application package metadata against deterministic rules without making speculative or unsupported claims.
- **`DeviceCapabilities`**: Represents legitimate hardware and OS properties discovered via standard Android APIs.
- **`AppInventoryEntry`**: Captures declared application metadata and runtime permission grant states.
- **`EvidenceMetadata`**: Formats cryptographic evidence records with SHA-256 and SHA-512 hashes.

### Service Layer (`org.ares.agent.service`)
- **`AresAgentService`**: Android Foreground Service displaying a persistent system notification (`POST_NOTIFICATIONS`) to maintain operational transparency.
- Runs periodic heartbeat telemetry loops (5–10s intervals).
- Handles graceful degradation upon network disconnect, transitioning running assessments to `INTERRUPTED`.

### Security Layer (`org.ares.agent.security`)
- **`KeystoreManager`**: Integrates with `AndroidKeyStore` to generate and protect HMAC-SHA256 signing keys. Private keys never leave secure hardware storage.
- **`DeviceIdentityManager`**: Generates unprivileged identifiers (`ares-android-xxxxxxxx`) without accessing restricted device IDs (IMEI, Serial, MAC).
- **`RedactingLogger`**: Prevents sensitive credentials, HMAC keys, and authorization tokens from leaking into system logs.

### Transport Layer (`org.ares.agent.transport`)
- **`AresTransport`**: Abstract communication contract allowing seamless switching between production HTTPS endpoints (`HttpTransport`) and offline test harnesses (`MockTransport`).

---

## 3. Finite State Machine

The Agent adheres to an explicit state machine:
- `OFFLINE`: Transport disconnected or waiting for network.
- `AUTHENTICATING`: Performing cryptographic handshake and exchanging `HELLO`.
- `AUTHORIZED`: Authenticated by backend and bound to an active legal assessment case.
- `BUSY`: Executing posture evaluation or inventory scan.
- `ERROR`: Protocol or unrecoverable hardware failure.
- `REVOKED`: Locked down by administrative policy. Assessment execution is strictly forbidden.
