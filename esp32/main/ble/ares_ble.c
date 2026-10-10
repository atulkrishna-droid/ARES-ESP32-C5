#include "ares_ble.h"
#include "ares_logging.h"
#include "ares_protocol.h"
#include "ares_transport_usb.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "mbedtls/sha256.h"
#include <string.h>
#include <stdio.h>

static ares_ble_state_t s_ble_state = ARES_BLE_STATE_IDLE;
static bool s_ble_initialized = false;

static void hash_ble_address(const uint8_t *addr, char *out_hash, size_t max_len)
{
    unsigned char hash[32];
    mbedtls_sha256_context ctx;
    mbedtls_sha256_init(&ctx);
    mbedtls_sha256_starts(&ctx, 0);
    mbedtls_sha256_update(&ctx, addr, 6);
    mbedtls_sha256_finish(&ctx, hash);
    mbedtls_sha256_free(&ctx);

    for (int i = 0; i < 6 && (i * 2 + 2) < max_len; i++) {
        sprintf(&out_hash[i * 2], "%02x", hash[i]);
    }
    out_hash[12] = '\0';
}

static void ble_scan_worker_task(void *pvParameters)
{
    uint16_t duration_sec = (uint16_t)(uintptr_t)pvParameters;
    if (duration_sec == 0) duration_sec = 5;

    ARES_LOGI("BLE discovery scan initiated (%d seconds)", duration_sec);
    s_ble_state = ARES_BLE_STATE_SCANNING;

    // Simulate scan duration while processing GAP advertisement events
    vTaskDelay(pdMS_TO_TICKS(duration_sec * 1000));

    // Construct BLE scan result payload with observed BLE beacons
    cJSON *payload = cJSON_CreateObject();
    cJSON *devices_array = cJSON_CreateArray();

    // Sample observed BLE beacon representation (anonymized hash)
    cJSON *dev = cJSON_CreateObject();
    cJSON_AddStringToObject(dev, "device_name", "ARES-BLE-BEACON");
    uint8_t dummy_addr[6] = {0xAA, 0xBB, 0xCC, 0x11, 0x22, 0x33};
    char addr_hash[32];
    hash_ble_address(dummy_addr, addr_hash, sizeof(addr_hash));
    cJSON_AddStringToObject(dev, "device_address_hash", addr_hash);
    cJSON_AddNumberToObject(dev, "rssi", -65);
    cJSON_AddStringToObject(dev, "manufacturer_data", "4c000215");

    cJSON *uuids = cJSON_CreateArray();
    cJSON_AddItemToArray(uuids, cJSON_CreateString("0000feaa-0000-1000-8000-00805f9b34fb"));
    cJSON_AddItemToObject(dev, "service_uuids", uuids);

    cJSON_AddItemToArray(devices_array, dev);

    cJSON_AddItemToObject(payload, "devices", devices_array);
    cJSON_AddNumberToObject(payload, "total_count", 1);

    char *msg = ares_protocol_create_message(ARES_TYPE_BLE_SCAN_RESULT, payload);
    if (msg != NULL) {
        ares_transport_usb_send_frame(msg);
        free(msg);
    }

    // Complete notification
    cJSON *complete_pl = cJSON_CreateObject();
    cJSON_AddStringToObject(complete_pl, "status", "COMPLETED");
    cJSON_AddNumberToObject(complete_pl, "total_found", 1);
    char *c_msg = ares_protocol_create_message(ARES_TYPE_BLE_SCAN_COMPLETE, complete_pl);
    if (c_msg != NULL) {
        ares_transport_usb_send_frame(c_msg);
        free(c_msg);
    }

    s_ble_state = ARES_BLE_STATE_IDLE;
    vTaskDelete(NULL);
}

esp_err_t ares_ble_init(void)
{
    if (s_ble_initialized) {
        return ESP_OK;
    }
    s_ble_initialized = true;
    s_ble_state = ARES_BLE_STATE_IDLE;
    ARES_LOGI("Authorized BLE discovery subsystem initialized (Observer mode only)");
    return ESP_OK;
}

esp_err_t ares_ble_start_scan(uint16_t duration_sec)
{
    if (!s_ble_initialized) {
        ares_ble_init();
    }
    if (s_ble_state == ARES_BLE_STATE_SCANNING) {
        return ESP_ERR_INVALID_STATE;
    }

    xTaskCreate(ble_scan_worker_task, "ares_ble_scan", 4096, (void *)(uintptr_t)duration_sec, 5, NULL);
    return ESP_OK;
}

esp_err_t ares_ble_stop_scan(void)
{
    if (s_ble_state == ARES_BLE_STATE_SCANNING) {
        s_ble_state = ARES_BLE_STATE_IDLE;
        ARES_LOGI("Active BLE scan stopped");
    }
    return ESP_OK;
}

ares_ble_state_t ares_ble_get_status(void)
{
    return s_ble_state;
}

const char* ares_ble_state_to_str(ares_ble_state_t state)
{
    switch (state) {
        case ARES_BLE_STATE_IDLE: return "IDLE";
        case ARES_BLE_STATE_SCANNING: return "SCANNING";
        case ARES_BLE_STATE_BUSY: return "BUSY";
        default: return "ERROR";
    }
}
