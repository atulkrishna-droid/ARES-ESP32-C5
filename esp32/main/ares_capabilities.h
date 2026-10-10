#ifndef ARES_CAPABILITIES_H
#define ARES_CAPABILITIES_H

#include <stdbool.h>
#include "cJSON.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    // Primary Radio & Core Hardware
    bool wifi_24;
    bool wifi_5;
    bool wifi6;
    bool ble;
    bool bluetooth_classic; // MUST be false on ESP32-C5
    bool ieee802154;
    bool zigbee;
    bool thread;
    bool usb;

    // Optional / Modular Peripherals (Runtime-detected)
    bool sd;
    bool gps;
    bool battery;
    bool display;
} ares_capabilities_t;

/**
 * Initialize and probe hardware capabilities.
 */
void ares_capabilities_init(void);

/**
 * Get current runtime capabilities.
 */
void ares_capabilities_get(ares_capabilities_t *out_caps);

/**
 * Update modular capability state (e.g. when SD card detected).
 */
void ares_capabilities_set_sd(bool present);

/**
 * Serialize capabilities into cJSON object for CAPABILITIES response.
 */
void ares_capabilities_populate_json(cJSON *json);

#ifdef __cplusplus
}
#endif

#endif // ARES_CAPABILITIES_H
