#include "ares_device.h"
#include "ares_logging.h"
#include "esp_system.h"
#include "esp_mac.h"
#include "esp_chip_info.h"
#include "esp_flash.h"
#include "esp_timer.h"
#include "esp_heap_caps.h"
#include <string.h>
#include <stdio.h>

static ares_device_info_t s_device_info;
static bool s_initialized = false;

esp_err_t ares_device_init(void)
{
    if (s_initialized) {
        return ESP_OK;
    }

    memset(&s_device_info, 0, sizeof(s_device_info));

    // 1. Read base factory MAC
    uint8_t mac[6] = {0};
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    snprintf(s_device_info.mac_address, sizeof(s_device_info.mac_address),
             "%02X:%02X:%02X:%02X:%02X:%02X",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    // 2. Generate persistent device ID
    snprintf(s_device_info.device_id, sizeof(s_device_info.device_id),
             "%s%02x%02x%02x%02x%02x%02x",
             ARES_DEVICE_ID_PREFIX,
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    // 3. Detect chip & revision
    esp_chip_info_t chip_info;
    esp_chip_info(&chip_info);

    strncpy(s_device_info.chip, ARES_CHIP_TARGET, sizeof(s_device_info.chip) - 1);
    snprintf(s_device_info.chip_revision, sizeof(s_device_info.chip_revision), "v%d.%d",
             chip_info.revision / 100, chip_info.revision % 100);

    strncpy(s_device_info.board_target, ARES_BOARD_TARGET, sizeof(s_device_info.board_target) - 1);
    strncpy(s_device_info.firmware_version, ARES_FIRMWARE_VERSION, sizeof(s_device_info.firmware_version) - 1);
    strncpy(s_device_info.protocol_version, ARES_PROTOCOL_VERSION, sizeof(s_device_info.protocol_version) - 1);

    // 4. Flash size detection
    uint32_t flash_size = 0;
    if (esp_flash_get_size(NULL, &flash_size) == ESP_OK) {
        s_device_info.flash_size_bytes = flash_size;
        snprintf(s_device_info.flash_size, sizeof(s_device_info.flash_size), "%luMB", (unsigned long)(flash_size / (1024 * 1024)));
    } else {
        strncpy(s_device_info.flash_size, ARES_FLASH_SIZE, sizeof(s_device_info.flash_size) - 1);
    }

    // 5. PSRAM detection
    size_t psram_free = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
    if (psram_free > 0) {
        snprintf(s_device_info.psram_size, sizeof(s_device_info.psram_size), "%luMB", (unsigned long)(psram_free / (1024 * 1024)));
    } else {
        strncpy(s_device_info.psram_size, "0MB", sizeof(s_device_info.psram_size) - 1);
    }

    s_initialized = true;
    ARES_LOGI("Device ID initialized: %s (%s, Rev: %s, Flash: %s)",
              s_device_info.device_id, s_device_info.chip,
              s_device_info.chip_revision, s_device_info.flash_size);

    return ESP_OK;
}

const char* ares_device_get_id(void)
{
    if (!s_initialized) {
        ares_device_init();
    }
    return s_device_info.device_id;
}

uint64_t ares_device_get_uptime_ms(void)
{
    return (uint64_t)(esp_timer_get_time() / 1000);
}

void ares_device_get_info(ares_device_info_t *info)
{
    if (info == NULL) return;
    if (!s_initialized) {
        ares_device_init();
    }
    memcpy(info, &s_device_info, sizeof(ares_device_info_t));
    info->free_heap_bytes = esp_get_free_heap_size();
    info->min_free_heap_bytes = esp_get_minimum_free_heap_size();
    info->uptime_ms = ares_device_get_uptime_ms();
}

void ares_device_populate_json(cJSON *json)
{
    if (json == NULL) return;
    ares_device_info_t info;
    ares_device_get_info(&info);

    cJSON_AddStringToObject(json, "device_id", info.device_id);
    cJSON_AddStringToObject(json, "chip", info.chip);
    cJSON_AddStringToObject(json, "chip_revision", info.chip_revision);
    cJSON_AddStringToObject(json, "board_target", info.board_target);
    cJSON_AddStringToObject(json, "firmware_version", info.firmware_version);
    cJSON_AddStringToObject(json, "protocol_version", info.protocol_version);
    cJSON_AddStringToObject(json, "flash_size", info.flash_size);
    cJSON_AddStringToObject(json, "psram_size", info.psram_size);
    cJSON_AddStringToObject(json, "mac_address", info.mac_address);
    cJSON_AddNumberToObject(json, "uptime_ms", (double)info.uptime_ms);
    cJSON_AddNumberToObject(json, "free_heap", (double)info.free_heap_bytes);
    cJSON_AddNumberToObject(json, "min_free_heap", (double)info.min_free_heap_bytes);
    cJSON_AddStringToObject(json, "usb_status", "CONNECTED");
}
