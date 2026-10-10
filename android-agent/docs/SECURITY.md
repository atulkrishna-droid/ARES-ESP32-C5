# ARES Android Agent — Security & Threat Model

## 1. Defensive Boundary & Ethical Constraints

The ARES Android Agent is designed strictly for **authorized, defensive, and owner-consented security posture assessments**.

### Prohibited Functionality
The agent explicitly does **NOT** implement and will **NEVER** contain:
- Lock-screen bypasses or PIN/biometric brute-forcing
- Credential theft, keystroke logging, or token extraction
- Stealth surveillance or hidden background persistence
- Arbitrary remote code execution (RCE) or interactive shells
- Unauthorized extraction of personal files, messages, or databases
- Wireless deauthentication or packet injection attacks

---

## 2. Cryptographic Storage & Android Keystore

- **Key Generation:** All signing keys are generated inside the `AndroidKeyStore` provider with hardware backing (TEE / StrongBox) where available.
- **HMAC-SHA256 Signing:** Each protocol frame transmitted to the backend is signed with an envelope HMAC-SHA256 digest.
- **Redaction:** `RedactingLogger` automatically scrubs patterns matching authentication tokens, private keys, HMAC secrets, and passwords before logging.
- **No Plaintext Export:** Private keys are non-exportable and never serialized to SQLite, SharedPreferences, or plain text files.

---

## 3. Case Authorization & Scoping

- **Explicit Scoping:** The agent cannot execute assessment jobs merely by being enrolled. Every assessment request requires an active `case_id` established by an authorized operator on the backend.
- **Scope Enforcement:** Operations outside the active legal case scope are rejected before execution.
- **Revocation:** If the backend revokes the device identity, the agent enters `REVOKED` state and refuses all diagnostic commands.

---

## 4. ADB & Developer Test Modes

ADB debugging is documented as an authorized diagnostic configuration. If enabled on the device:
- The agent reports `ANDROID-DEV-001` as a low-severity finding to ensure awareness.
- ADB is never used to circumvent device security controls on unauthorized targets.
