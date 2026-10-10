#include "ares_wifi.h"
#include "ares_logging.h"
#include "ares_protocol.h"
#include "ares_transport_usb.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "mbedtls/sha256.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>
#include <stdio.h>

static ares_wifi_state_t s_wifi_state = ARES_WIFI_STATE_IDLE;
static bool s_driver_initialized = false;

static const char* auth_mode_to_str(wifi_auth_mode_t auth_mode)
{
    switch (auth_mode) {
        case WIFI_AUTH_OPEN: return "OPEN";
        case WIFI_AUTH_WEP: return "WEP";
        case WIFI_AUTH_WPA_PSK: return "WPA";
        case WIFI_AUTH_WPA2_PSK: return "WPA2";
        case WIFI_AUTH_WPA_WPA2_PSK: return "WPA_WPA2";
        case WIFI_AUTH_WPA3_PSK: return "WPA3";
        case WIFI_AUTH_WPA2_WPA3_PSK: return "WPA2_WPA3";
        default: return "UNKNOWN";
    }
}

static void hash_bssid(const uint8_t *bssid, char *out_hash, size_t max_len)
{
    unsigned char hash[32];
    mbedtls_sha256_context ctx;
    mbedtls_sha256_init(&ctx);
    mbedtls_sha256_starts(&ctx, 0);
    mbedtls_sha256_update(&ctx, bssid, 6);
    mbedtls_sha256_finish(&ctx, hash);
    mbedtls_sha256_free(&ctx);

    // Take first 12 hex chars for compact fingerprint
    for (int i = 0; i < 6 && (i * 2 + 2) < max_len; i++) {
        sprintf(&out_hash[i * 2], "%02x", hash[i]);
    }
    out_hash[12] = '\0';
}

static uint16_t channel_to_freq(uint8_t channel, const char **band_out)
{
    if (channel >= 1 && channel <= 14) {
        if (band_out) *band_out = "2.4GHz";
        return (channel == 14) ? 2484 : (2407 + channel * 5);
    } else if (channel >= 36 && channel <= 177) {
        if (band_out) *band_out = "5GHz";
        return 5000 + channel * 5;
    }
    if (band_out) *band_out = "2.4GHz";
    return 2412;
}

static void wifi_scan_worker_task(void *pvParameters)
{
    ARES_LOGI("Wi-Fi scan task initiated on dual-band RF core");
    s_wifi_state = ARES_WIFI_STATE_SCANNING;

    wifi_scan_config_t scan_config = {
        .ssid = NULL,
        .bssid = NULL,
        .channel = 0, // scan all channels
        .show_hidden = true,
        .scan_type = WIFI_SCAN_TYPE_ACTIVE,
    };

    esp_err_t err = esp_wifi_scan_start(&scan_config, true); // blocking scan in worker task
    if (err == ESP_OK) {
        uint16_t ap_count = 0;
        esp_wifi_scan_get_ap_num(&ap_count);
        ARES_LOGI("Scan complete: found %d access points", ap_count);

        if (ap_count > 0) {
            wifi_ap_record_t *ap_records = malloc(sizeof(wifi_ap_record_t) * ap_count);
            if (ap_records != NULL) {
                ESP_ERROR_CHECK(esp_wifi_scan_get_ap_records(&ap_count, ap_records));

                cJSON *payload = cJSON_CreateObject();
                cJSON *net_array = cJSON_CreateArray();

                for (int i = 0; i < ap_count; i++) {
                    cJSON *ap_item = cJSON_CreateObject();
                    cJSON_AddStringToObject(ap_item, "ssid", (char *)ap_records[i].ssid);

                    char bssid_h[32];
                    hash_bssid(ap_records[i].bssid, bssid_h, sizeof(bssid_h));
                    cJSON_AddStringToObject(ap_item, "bssid_hash", bssid_h);

                    cJSON_AddNumberToObject(ap_item, "channel", ap_records[i].primary);
                    const char *band_name = NULL;
                    uint16_t freq = channel_to_freq(ap_records[i].primary, &band_name);
                    cJSON_AddNumberToObject(ap_item, "frequency", freq);
                    cJSON_AddStringToObject(ap_item, "band", band_name);
                    cJSON_AddNumberToObject(ap_item, "rssi", ap_records[i].rssi);
                    cJSON_AddStringToObject(ap_item, "security_type", auth_mode_to_str(ap_records[i].authmode));

                    cJSON_AddItemToArray(net_array, ap_item);
                }

                cJSON_AddItemToObject(payload, "networks", net_array);
                cJSON_AddNumberToObject(payload, "total_count", ap_count);

                char *msg = ares_protocol_create_message(ARES_TYPE_WIFI_SCAN_RESULT, payload);
                if (msg != NULL) {
                    ares_transport_usb_send_frame(msg);
                    free(msg);
                }
                free(ap_records);
            }
        }

        // Send SCAN_COMPLETE event
        cJSON *done_payload = cJSON_CreateObject();
        cJSON_AddStringToObject(done_payload, "status", "COMPLETED");
        cJSON_AddNumberToObject(done_payload, "total_found", ap_count);
        char *complete_msg = ares_protocol_create_message(ARES_TYPE_WIFI_SCAN_COMPLETE, done_payload);
        if (complete_msg != NULL) {
            ares_transport_usb_send_frame(complete_msg);
            free(complete_msg);
        }
    } else {
        ARES_LOGE("esp_wifi_scan_start failed: 0x%x", err);
    }

    s_wifi_state = ARES_WIFI_STATE_IDLE;
    vTaskDelete(NULL);
}

esp_err_t ares_wifi_init(void)
{
    if (s_driver_initialized) {
        return ESP_OK;
    }

    esp_netif_init();
    esp_event_loop_create_default();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_err_t err = esp_wifi_init(&cfg);
    if (err != ESP_OK) {
        ARES_LOGE("Failed to init Wi-Fi: 0x%x", err);
        return err;
    }

    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_start();

    s_driver_initialized = true;
    s_wifi_state = ARES_WIFI_STATE_IDLE;
    ARES_LOGI("Authorized Wi-Fi subsystem initialized (ESP32-C5 2.4/5GHz Dual-Band)");
    return ESP_OK;
}

esp_err_t ares_wifi_start_scan(uint16_t dwell_time_ms, const char *band_filter)
{
    if (!s_driver_initialized) {
        ares_wifi_init();
    }
    if (s_wifi_state == ARES_WIFI_STATE_SCANNING) {
        return ESP_ERR_INVALID_STATE;
    }

    // Spawn scan task on FreeRTOS
    xTaskCreate(wifi_scan_worker_task, "ares_wifi_scan", 4096, NULL, 5, NULL);
    return ESP_OK;
}

esp_err_t ares_wifi_stop_scan(void)
{
    if (s_wifi_state == ARES_WIFI_STATE_SCANNING) {
        esp_wifi_scan_stop();
        s_wifi_state = ARES_WIFI_STATE_IDLE;
        ARES_LOGI("Active Wi-Fi scan aborted by operator");
    }
    return ESP_OK;
}

ares_wifi_state_t ares_wifi_get_status(void)
{
    return s_wifi_state;
}

const char* ares_wifi_state_to_str(ares_wifi_state_t state)
{
    switch (state) {
        case ARES_WIFI_STATE_IDLE: return "IDLE";
        case ARES_WIFI_STATE_SCANNING: return "SCANNING";
        case ARES_WIFI_STATE_BUSY: return "BUSY";
        default: return "ERROR";
    }
}
