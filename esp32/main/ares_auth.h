#ifndef ARES_AUTH_H
#define ARES_AUTH_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ARES_SIGNATURE_HEX_LEN 64 // 256 bits = 32 bytes = 64 hex chars

/**
 * Initialize authentication subsystem and load provisioned key.
 */
esp_err_t ares_auth_init(void);

/**
 * Set or update the active HMAC signing key.
 */
esp_err_t ares_auth_set_key(const uint8_t *key, size_t key_len);

/**
 * Check if a valid HMAC key is loaded.
 */
bool ares_auth_has_key(void);

/**
 * Generate HMAC-SHA256 signature over canonical message components.
 * Out signature is 64-char lowercase hex string + null terminator.
 */
esp_err_t ares_auth_compute_signature(
    const char *protocol,
    const char *type,
    const char *device_id,
    const char *timestamp,
    uint64_t sequence,
    const char *payload_json_str,
    char *out_sig_hex,
    size_t out_sig_max_len
);

/**
 * Verify incoming message signature.
 * Constant-time comparison to prevent side-channel timing attacks.
 */
bool ares_auth_verify_signature(
    const char *protocol,
    const char *type,
    const char *device_id,
    const char *timestamp,
    uint64_t sequence,
    const char *payload_json_str,
    const char *expected_sig_hex
);

#ifdef __cplusplus
}
#endif

#endif // ARES_AUTH_H
