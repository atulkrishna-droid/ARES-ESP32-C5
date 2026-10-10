# ARES Security Model & Authorization Boundaries

## 1. Ethical & Authorized Operational Boundaries

ARES is an **Authorized Security Assessment Platform**. It explicitly refuses to facilitate malicious exploitation, covert monitoring, or offensive network disruption.

### Prohibited Functionality & Anti-Features
1. **No Lock Screen Bypasses**: No PIN brute-forcing or credential extraction modules.
2. **No Spyware / Clandestine Monitoring**: No silent background audio capture, SMS theft, or photo extraction.
3. **No Wireless Disruption**: No 802.11 deauthentication attacks, packet injection, or beacon flooding.
4. **No Arbitrary Remote Command Execution**: The backend rejects arbitrary shell commands, raw binary flashing, or unverified firmware updates.

---

## 2. Device Authorization State Machine

A device cannot participate in an assessment unless it passes through formal state gates:

```
UNREGISTERED
     |
     v
ENROLLMENT_REQUESTED
     |
     v
PENDING_APPROVAL
     |
     v
 AUTHORIZED
     |
     v
   ACTIVE  <---> BUSY (Locked by active assessment)
     |
     v
  REVOKED
```

---

## 3. Case Scoping Boundaries

Every assessment must define a strict scope document:
```json
{
  "device_ids": ["DEVICE-UUID-1"],
  "network_ids": ["CORP-SSID"],
  "allowed_operations": [
    "DEVICE_INVENTORY",
    "SECURITY_POSTURE",
    "WIFI_DISCOVERY"
  ],
  "expires_at": "2026-10-27T12:00:00Z"
}
```
Any assessment attempt that requests operations outside this set is aborted with `SCOPE_VIOLATION`.

---

## 4. Tamper-Evident Audit Ledger

Audit entries are hashed using canonical JSON and chained mathematically:
$$\text{event\_hash}_n = \text{SHA256}(\text{event\_hash}_{n-1} \parallel \text{canonical\_json}(\text{event}_n))$$

The verification endpoint (`GET /api/v1/audit/verify`) ensures that if any past record is modified, inserted, or deleted, the broken hash chain is instantly flagged.
