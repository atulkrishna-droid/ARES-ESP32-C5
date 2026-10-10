#include "ares_secure_storage.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_log.h"
#include "ares_logging.h"
#include <string.h>

static nvs_handle_t s_nvs_handle;
static bool s_initialized = false;

esp_err_t ares_secure_storage_initialize(void)
{
    if (s_initialized) {
        return ESP_OK;
    }

    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    if (err != ESP_OK) {
        ARES_LOGE("NVS flash init failed: 0x%x", err);
        return err;
    }

    // Attempt to open dedicated secure namespace
    err = nvs_open(ARES_SEC_NAMESPACE, NVS_READWRITE, &s_nvs_handle);
    if (err != ESP_OK) {
        ARES_LOGE("Failed to open NVS namespace '%s': 0x%x", ARES_SEC_NAMESPACE, err);
        return err;
    }

    s_initialized = true;
    ARES_LOGI("Secure storage initialized successfully");
    return ESP_OK;
}

esp_err_t ares_secure_storage_store_secret(const char *key, const uint8_t *data, size_t len)
{
    if (!s_initialized || key == NULL || data == NULL || len == 0) {
        return ESP_ERR_INVALID_ARG;
    }

    esp_err_t err = nvs_set_blob(s_nvs_handle, key, data, len);
    if (err != ESP_OK) {
        ARES_LOGE("Failed to set secret blob: 0x%x", err);
        return err;
    }

    err = nvs_commit(s_nvs_handle);
    if (err != ESP_OK) {
        ARES_LOGE("Failed to commit secret blob: 0x%x", err);
        return err;
    }

    return ESP_OK;
}

esp_err_t ares_secure_storage_read_secret(const char *key, uint8_t *out_data, size_t max_len, size_t *out_len)
{
    if (!s_initialized || key == NULL || out_data == NULL || out_len == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    size_t required_len = 0;
    esp_err_t err = nvs_get_blob(s_nvs_handle, key, NULL, &required_len);
    if (err != ESP_OK) {
        return err;
    }

    if (required_len > max_len) {
        return ESP_ERR_INVALID_SIZE;
    }

    err = nvs_get_blob(s_nvs_handle, key, out_data, &required_len);
    if (err == ESP_OK) {
        *out_len = required_len;
    }
    return err;
}

esp_err_t ares_secure_storage_delete_secret(const char *key)
{
    if (!s_initialized || key == NULL) {
        return ESP_ERR_INVALID_ARG;
    }

    esp_err_t err = nvs_erase_key(s_nvs_handle, key);
    if (err == ESP_OK) {
        nvs_commit(s_nvs_handle);
    }
    return err;
}

bool ares_secure_storage_has_secret(const char *key)
{
    if (!s_initialized || key == NULL) {
        return false;
    }
    size_t len = 0;
    esp_err_t err = nvs_get_blob(s_nvs_handle, key, NULL, &len);
    return (err == ESP_OK && len > 0);
}
