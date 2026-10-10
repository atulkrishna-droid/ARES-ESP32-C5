#ifndef ARES_SECURE_STORAGE_H
#define ARES_SECURE_STORAGE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ARES_SEC_NAMESPACE "ares_sec"
#define ARES_KEY_HMAC_SECRET "hmac_secret"
#define ARES_KEY_DEVICE_ID   "device_id"

/**
 * Initialize secure storage partition and NVS handles.
 */
esp_err_t ares_secure_storage_initialize(void);

/**
 * Store a sensitive secret in encrypted/isolated NVS partition.
 */
esp_err_t ares_secure_storage_store_secret(const char *key, const uint8_t *data, size_t len);

/**
 * Read a secret from secure storage.
 */
esp_err_t ares_secure_storage_read_secret(const char *key, uint8_t *out_data, size_t max_len, size_t *out_len);

/**
 * Delete a secret from secure storage.
 */
esp_err_t ares_secure_storage_delete_secret(const char *key);

/**
 * Check if a secret exists in storage.
 */
bool ares_secure_storage_has_secret(const char *key);

#ifdef __cplusplus
}
#endif

#endif // ARES_SECURE_STORAGE_H
