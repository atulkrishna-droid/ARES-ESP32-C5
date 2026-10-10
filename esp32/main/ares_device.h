#ifndef ARES_DEVICE_H
#define ARES_DEVICE_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "cJSON.h"
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ARES_FIRMWARE_VERSION  "1.0.0"
#define ARES_PROTOCOL_VERSION  "ARES/1.0"
#define ARES_CHIP_TARGET       "ESP32-C5"
#define ARES_BOARD_TARGET      "ESP32-C5-DevKitC-1"
#define ARES_FLASH_SIZE        "8MB"
#define ARES_DEVICE_ID_PREFIX  "ares-esp32-c5-"

typedef struct {
    char device_id[48];
    char chip[16];
    char chip_revision[16];
    char board_target[32];
    char firmware_version[16];
    char protocol_version[16];
    char flash_size[16];
    char psram_size[16];
    char mac_address[24];
    uint32_t flash_size_bytes;
    uint32_t free_heap_bytes;
    uint32_t min_free_heap_bytes;
    uint64_t uptime_ms;
} ares_device_info_t;

/**
 * Initialize device identification subsystem.
 */
esp_err_t ares_device_init(void);

/**
 * Get cached persistent device ID (e.g. ares-esp32-c5-aabbccddeeff).
 */
const char* ares_device_get_id(void);

/**
 * Get populated device info structure.
 */
void ares_device_get_info(ares_device_info_t *info);

/**
 * Populate cJSON object with device info for ARES/1.0 DEVICE_INFO payload.
 */
void ares_device_populate_json(cJSON *json);

/**
 * Returns system uptime in milliseconds.
 */
uint64_t ares_device_get_uptime_ms(void);

#ifdef __cplusplus
}
#endif

#endif // ARES_DEVICE_H
