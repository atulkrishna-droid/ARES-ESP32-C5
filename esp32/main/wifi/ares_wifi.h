#ifndef ARES_WIFI_H
#define ARES_WIFI_H

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
#include "cJSON.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    ARES_WIFI_STATE_IDLE = 0,
    ARES_WIFI_STATE_SCANNING,
    ARES_WIFI_STATE_BUSY,
    ARES_WIFI_STATE_ERROR
} ares_wifi_state_t;

typedef struct {
    char ssid[33];
    char bssid_hash[32]; // Hashed representation of MAC
    uint8_t channel;
    uint16_t frequency; // MHz (e.g. 2412, 5180)
    char band[8];       // "2.4GHz" or "5GHz"
    int8_t rssi;
    char security_type[16]; // OPEN, WEP, WPA, WPA2, WPA3
} ares_wifi_ap_record_t;

/**
 * Initialize ESP32-C5 Wi-Fi driver in station/monitor observer mode.
 */
esp_err_t ares_wifi_init(void);

/**
 * Start non-blocking Wi-Fi scan on 2.4GHz and/or 5GHz bands.
 * @param dwell_time_ms Scan time per channel in milliseconds
 * @param band_filter "ALL", "2.4GHz", or "5GHz"
 */
esp_err_t ares_wifi_start_scan(uint16_t dwell_time_ms, const char *band_filter);

/**
 * Stop active Wi-Fi scan immediately.
 */
esp_err_t ares_wifi_stop_scan(void);

/**
 * Get current Wi-Fi subsystem operational state.
 */
ares_wifi_state_t ares_wifi_get_status(void);

/**
 * Get state as string for telemetry.
 */
const char* ares_wifi_state_to_str(ares_wifi_state_t state);

#ifdef __cplusplus
}
#endif

#endif // ARES_WIFI_H
