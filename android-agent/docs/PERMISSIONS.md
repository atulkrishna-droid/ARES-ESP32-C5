# ARES Android Agent — Permission Transparency Matrix

In accordance with Section 10 of the specification, this document describes every permission and platform API utilized by the ARES Android Agent.

---

## Permission Matrix

| Permission / API | Purpose / Why ARES Needs It | Min Android Version | Runtime Permission? | Optional? | Fallback / Behavior if Denied |
|---|---|---|---|---|---|
| `android.permission.INTERNET` | Establishing TLS 1.3 encrypted connection to ARES backend. | API 1 (Android 1.0) | No (Normal) | **Required** | Agent transitions to `OFFLINE` state; assessments cannot be synchronized. |
| `android.permission.ACCESS_NETWORK_STATE` | Inspecting network connection indicators (Wi-Fi, Cellular, VPN presence). | API 1 (Android 1.0) | No (Normal) | Optional | Assumes standard default network without interface-specific telemetry. |
| `android.permission.FOREGROUND_SERVICE` | Maintaining persistent assessment execution and periodic heartbeat without OS killing. | API 28 (Android 9) | No (Normal) | **Required** | Background assessments terminated when app loses focus; heartbeat ceases. |
| `android.permission.FOREGROUND_SERVICE_SPECIAL_USE` | Declares special-use background diagnostic service type on Android 14+. | API 34 (Android 14) | No (Normal) | **Required (API 34+)** | Foreground service cannot launch on Android 14+ devices. |
| `android.permission.POST_NOTIFICATIONS` | Displays ongoing system notification informing user that assessment service is active. | API 33 (Android 13) | Yes (Dangerous) | Optional | Notification suppressed; service continues to run but without visual indicator. |
| `android.permission.QUERY_ALL_PACKAGES` | Inspecting installed package metadata and permissions for application inventory. | API 30 (Android 11) | No (Special App Access) | Optional | Gracefully falls back to querying self-package and common launcher activities. |

---

## Prohibited Behaviors & APIs

The ARES Android Agent **NEVER** declares or attempts to access:
- `READ_PRIVILEGED_PHONE_STATE` (hardware IMEI/IMSI extraction)
- `BIND_ACCESSIBILITY_SERVICE` (screen scraping / keylogging)
- `READ_SMS` / `RECEIVE_SMS` (message extraction)
- `READ_CONTACTS` / `READ_CALL_LOG` (personal data extraction)
- `MANAGE_EXTERNAL_STORAGE` (arbitrary user file extraction)
- Root exploitation or su binaries
