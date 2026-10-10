# ARES Android Agent — Capability Discovery Model

## 1. Discovery Architecture

The Android Agent discovers hardware and operating system capabilities through legitimate Android framework APIs (`Build`, `ConnectivityManager`, `Settings.Global`).

```json
{
  "android_version": "14",
  "sdk_version": 34,
  "security_patch": "2026-08-01",
  "device_model": "Pixel 8 Pro",
  "manufacturer": "Google",
  "app_version": "1.0.0",
  "network_capabilities": ["WIFI", "INTERNET"],
  "vpn_state_if_available": false,
  "developer_options_state_if_available": false,
  "debuggable_state_if_available": false,
  "permissions_supported": ["INTERNET", "ACCESS_NETWORK_STATE", "FOREGROUND_SERVICE"],
  "management_state_if_available": "UNMANAGED",
  "encryption_status": "ENCRYPTED"
}
```

---

## 2. API Sources

| Capability Metric | Android Source API | Fallback if Unavailable |
|---|---|---|
| `android_version` | `android.os.Build.VERSION.RELEASE` | `"Unknown"` |
| `sdk_version` | `android.os.Build.VERSION.SDK_INT` | `26` (Min SDK) |
| `security_patch` | `android.os.Build.VERSION.SECURITY_PATCH` | `null` (Triggers `ANDROID-SEC-001`) |
| `device_model` | `android.os.Build.MODEL` | `"Generic Android"` |
| `manufacturer` | `android.os.Build.MANUFACTURER` | `"Generic"` |
| `network_capabilities` | `ConnectivityManager.getNetworkCapabilities()` | `["INTERNET"]` |
| `vpn_state_if_available` | `NetworkCapabilities.hasTransport(TRANSPORT_VPN)` | `false` |
| `developer_options` | `Settings.Global.DEVELOPMENT_SETTINGS_ENABLED` | `false` |
| `debuggable_state` | `Settings.Global.ADB_ENABLED` | `false` |
| `encryption_status` | `DevicePolicyManager.getStorageEncryptionStatus()` | `"ENCRYPTED"` |
