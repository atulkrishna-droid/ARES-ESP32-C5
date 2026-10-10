#ifndef ARES_BLE_H
#define ARES_BLE_H

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    ARES_BLE_STATE_IDLE = 0,
    ARES_BLE_STATE_SCANNING,
    ARES_BLE_STATE_BUSY,
    ARES_BLE_STATE_ERROR
} ares_ble_state_t;

/**
 * Initialize Bluetooth Low Energy discovery subsystem.
 * Strictly configured as passive/active observer (No pairing).
 */
esp_err_t ares_ble_init(void);

/**
 * Start BLE discovery scan.
 * @param duration_sec Scan duration in seconds
 */
esp_err_t ares_ble_start_scan(uint16_t duration_sec);

/**
 * Stop active BLE scan.
 */
esp_err_t ares_ble_stop_scan(void);

/**
 * Get current BLE state.
 */
ares_ble_state_t ares_ble_get_status(void);

/**
 * Get state string for telemetry.
 */
const char* ares_ble_state_to_str(ares_ble_state_t state);

#ifdef __cplusplus
}
#endif

#endif // ARES_BLE_H
