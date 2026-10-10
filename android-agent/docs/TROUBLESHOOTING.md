# ARES Android Agent — Troubleshooting Guide

## 1. Network & Connectivity Issues

### Error: `Connect probe failed: /10.0.2.2:8000 refused`
- **Cause:** The backend server is not running or listening only on `127.0.0.1`.
- **Solution:** Ensure the FastAPI backend is launched with `--host 0.0.0.0`:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```

### Cleartext Traffic Prohibited Error
- **Cause:** Android 9+ prohibits cleartext HTTP by default.
- **Solution:** Confirm that `res/xml/network_security_config.xml` includes `10.0.2.2` in `domain-config cleartextTrafficPermitted="true"`, or deploy backend with valid TLS certificates.

---

## 2. Permission Issues

### Incomplete Application Inventory
- **Cause:** Android 11+ restricts package visibility unless `QUERY_ALL_PACKAGES` is declared or specific intents are listed.
- **Solution:** The agent declares `QUERY_ALL_PACKAGES` for security auditing. On production stores, Google Play requires security tool justification. In testing/developer builds, the permission is granted automatically.

### Notification Not Showing
- **Cause:** Android 13+ requires runtime permission `POST_NOTIFICATIONS`.
- **Solution:** Allow notifications when prompted by `MainActivity` on first launch.

---

## 3. Revocation Lock
- **Cause:** An operator clicked Revoke Device on the ARES dashboard or via API.
- **Behavior:** The agent permanently transitions to `REVOKED` state and rejects commands.
- **Solution:** Re-enroll with a new device identity or clear application storage.
