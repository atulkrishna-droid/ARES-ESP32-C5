# Android commissioning status

The Android application currently creates its signing key locally in Android Keystore. The backend validates Android envelopes with the deployment-wide `ANDROID_HMAC_SECRET` (or its development-only fallback). There is no secure exchange that makes those keys the same. A digest of an HMAC key is not a public key and must not be registered as one.

The Android app does not call `/android/enroll`. The enrollment endpoint now requires an authenticated user with `device.enroll`; it creates a `PENDING_APPROVAL` device and does not grant case access. HELLO remains a separate request and reports `READY` when no case authorization exists.

Until per-device key commissioning exists, the app must not treat a handshake response as authenticated. It verifies response signatures with its local key and rejects unsigned or invalid responses. A real request will also fail backend verification unless the backend is provisioned with the corresponding signer, which this app does not export or transmit.

## Required commissioning work

1. Configure the backend and Android transport to use HTTPS with a trusted certificate and hostname validation.
2. Replace the global Android HMAC key with a per-device asymmetric identity: generate a non-exportable signing key pair in Android Keystore and register only its actual public key.
3. Bind public-key registration to an authenticated operator flow with `device.enroll` permission. Keep the resulting device `PENDING_APPROVAL`; make operator device approval and case authorization separate actions.
4. Store the public key per device on the backend and verify signed envelopes against that key. Use a challenge/nonce and signed server responses so the device can authenticate the backend and the backend can prove device-key possession without sharing private key material.
5. Add isolated tests for enrollment authorization, public-key binding, challenge replay, signed response verification, and the PENDING_APPROVAL lifecycle before enabling the commissioning flow.

No key is embedded in the APK or sourced from an unauthenticated enrollment response. An administrator must choose and deploy the backend trust configuration and approve the initial commissioning workflow before an authenticated end-to-end handshake can succeed.
