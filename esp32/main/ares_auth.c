#include "ares_auth.h"
#include "ares_secure_storage.h"
#include "ares_logging.h"
#include "mbedtls/md.h"
#include <string.h>
#include <stdio.h>

#define ARES_DEFAULT_DEV_SECRET "ares-dev-secret-esp32-key-min-32-chars-2026"

static uint8_t s_hmac_key[64];
static size_t s_hmac_key_len = 0;
static bool s_has_key = false;

// Constant-time buffer comparison to prevent timing side channels
static int constant_time_memcmp(const void *a, const void *b, size_t size)
{
    const uint8_t *ua = (const uint8_t *)a;
    const uint8_t *ub = (const uint8_t *)b;
    int result = 0;
    for (size_t i = 0; i < size; i++) {
        result |= ua[i] ^ ub[i];
    }
    return result;
}

esp_err_t ares_auth_init(void)
{
    s_has_key = false;
    s_hmac_key_len = 0;

    // Check if key is persisted in secure storage
    if (ares_secure_storage_has_secret(ARES_KEY_HMAC_SECRET)) {
        size_t read_len = 0;
        esp_err_t err = ares_secure_storage_read_secret(
            ARES_KEY_HMAC_SECRET, s_hmac_key, sizeof(s_hmac_key), &read_len);
        if (err == ESP_OK && read_len > 0) {
            s_hmac_key_len = read_len;
            s_has_key = true;
            ARES_LOGI("HMAC key loaded from secure storage");
            return ESP_OK;
        }
    }

    // Fall back to default development key for zero-config lab testing
    s_hmac_key_len = strlen(ARES_DEFAULT_DEV_SECRET);
    memcpy(s_hmac_key, ARES_DEFAULT_DEV_SECRET, s_hmac_key_len);
    s_has_key = true;
    ARES_LOGI("Initialized with development HMAC secret (Lab mode)");
    return ESP_OK;
}

esp_err_t ares_auth_set_key(const uint8_t *key, size_t key_len)
{
    if (key == NULL || key_len == 0 || key_len > sizeof(s_hmac_key)) {
        return ESP_ERR_INVALID_ARG;
    }
    memcpy(s_hmac_key, key, key_len);
    s_hmac_key_len = key_len;
    s_has_key = true;

    // Persist to secure storage
    ares_secure_storage_store_secret(ARES_KEY_HMAC_SECRET, key, key_len);
    ARES_LOGI("HMAC key updated and persisted");
    return ESP_OK;
}

bool ares_auth_has_key(void)
{
    return s_has_key;
}

esp_err_t ares_auth_compute_signature(
    const char *protocol,
    const char *type,
    const char *device_id,
    const char *timestamp,
    uint64_t sequence,
    const char *payload_json_str,
    char *out_sig_hex,
    size_t out_sig_max_len
) {
    if (!s_has_key || out_sig_hex == NULL || out_sig_max_len <= ARES_SIGNATURE_HEX_LEN) {
        return ESP_ERR_INVALID_ARG;
    }

    // Canonical representation string:
    // canonical_repr = f"{envelope.protocol}|{envelope.type}|{envelope.device_id}|{envelope.timestamp}|{envelope.sequence}|{canonical_payload_json}"
    char header_buf[256];
    int header_len = snprintf(header_buf, sizeof(header_buf), "%s|%s|%s|%s|%llu|",
                              protocol ? protocol : "",
                              type ? type : "",
                              device_id ? device_id : "",
                              timestamp ? timestamp : "",
                              (unsigned long long)sequence);
    if (header_len < 0 || header_len >= sizeof(header_buf)) {
        return ESP_ERR_INVALID_SIZE;
    }

    const char *payload_str = payload_json_str ? payload_json_str : "{}";
    size_t payload_len = strlen(payload_str);

    // Compute HMAC-SHA256 via mbedtls
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);

    const mbedtls_md_info_t *md_info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    if (md_info == NULL) {
        mbedtls_md_free(&ctx);
        return ESP_FAIL;
    }

    if (mbedtls_md_hmac_starts(&ctx, s_hmac_key, s_hmac_key_len) != 0) {
        mbedtls_md_free(&ctx);
        return ESP_FAIL;
    }

    mbedtls_md_hmac_update(&ctx, (const unsigned char *)header_buf, header_len);
    mbedtls_md_hmac_update(&ctx, (const unsigned char *)payload_str, payload_len);

    unsigned char hmac_out[32];
    mbedtls_md_hmac_finish(&ctx, hmac_out);
    mbedtls_md_free(&ctx);

    // Format to lowercase hex string
    for (int i = 0; i < 32; i++) {
        sprintf(&out_sig_hex[i * 2], "%02x", hmac_out[i]);
    }
    out_sig_hex[64] = '\0';

    return ESP_OK;
}

bool ares_auth_verify_signature(
    const char *protocol,
    const char *type,
    const char *device_id,
    const char *timestamp,
    uint64_t sequence,
    const char *payload_json_str,
    const char *expected_sig_hex
) {
    if (expected_sig_hex == NULL || strlen(expected_sig_hex) != ARES_SIGNATURE_HEX_LEN) {
        return false;
    }

    char computed_sig[ARES_SIGNATURE_HEX_LEN + 1];
    if (ares_auth_compute_signature(protocol, type, device_id, timestamp, sequence,
                                    payload_json_str, computed_sig, sizeof(computed_sig)) != ESP_OK) {
        return false;
    }

    return (constant_time_memcmp(computed_sig, expected_sig_hex, ARES_SIGNATURE_HEX_LEN) == 0);
}
