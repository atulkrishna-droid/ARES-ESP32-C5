#include "ares_telemetry.h"
#include "ares_logging.h"
#include "ares_protocol.h"
#include "ares_transport_usb.h"
#include "ares_device.h"
#include "ares_wifi.h"
#include "ares_ble.h"
#include "ares_802154.h"
#include "ares_storage.h"
#include "esp_heap_caps.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static uint32_t s_interval_ms = ARES_HEARTBEAT_INTERVAL_MS;
static TaskHandle_t s_telemetry_task_handle = NULL;

esp_err_t ares_telemetry_send_heartbeat(void)
{
    ares_device_info_t dev_info;
    ares_device_get_info(&dev_info);

    cJSON *payload = cJSON_CreateObject();
    cJSON_AddNumberToObject(payload, "uptime_ms", (double)dev_info.uptime_ms);
    cJSON_AddNumberToObject(payload, "free_heap", (double)dev_info.free_heap_bytes);
    cJSON_AddNumberToObject(payload, "min_free_heap", (double)dev_info.min_free_heap_bytes);
    cJSON_AddNumberToObject(payload, "free_psram", (double)heap_caps_get_free_size(MALLOC_CAP_SPIRAM));

    cJSON_AddStringToObject(payload, "wifi_state", ares_wifi_state_to_str(ares_wifi_get_status()));
    cJSON_AddStringToObject(payload, "ble_state", ares_ble_state_to_str(ares_ble_get_status()));
    cJSON_AddStringToObject(payload, "ieee802154_state", ares_802154_state_to_str(ares_802154_get_state()));
    cJSON_AddStringToObject(payload, "storage_state", ares_storage_state_to_str(ares_storage_get_state()));
    cJSON_AddStringToObject(payload, "usb_state", ares_transport_usb_is_connected() ? "CONNECTED" : "OFFLINE");
    cJSON_AddStringToObject(payload, "firmware_version", dev_info.firmware_version);

    char *msg = ares_protocol_create_message(ARES_TYPE_HEARTBEAT, payload);
    if (msg == NULL) {
        return ESP_FAIL;
    }

    esp_err_t err = ares_transport_usb_send_frame(msg);
    free(msg);
    return err;
}

static void telemetry_worker_task(void *pvParameters)
{
    ARES_LOGI("Periodic telemetry worker started (Interval: %lu ms)", (unsigned long)s_interval_ms);

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(s_interval_ms));
        ares_telemetry_send_heartbeat();
    }
}

esp_err_t ares_telemetry_init(void)
{
    if (s_telemetry_task_handle != NULL) {
        return ESP_OK;
    }

    xTaskCreate(telemetry_worker_task, "ares_telemetry", 3072, NULL, 3, &s_telemetry_task_handle);
    ARES_LOGI("Telemetry subsystem initialized");
    return ESP_OK;
}

void ares_telemetry_set_interval(uint32_t interval_ms)
{
    s_interval_ms = (interval_ms < 1000) ? 1000 : interval_ms;
}
