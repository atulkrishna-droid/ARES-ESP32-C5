#ifndef ARES_TELEMETRY_H
#define ARES_TELEMETRY_H

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ARES_HEARTBEAT_INTERVAL_MS 5000 // 5 seconds default

/**
 * Initialize telemetry subsystem and start FreeRTOS background task.
 */
esp_err_t ares_telemetry_init(void);

/**
 * Trigger immediate sending of a HEARTBEAT message.
 */
esp_err_t ares_telemetry_send_heartbeat(void);

/**
 * Set custom heartbeat interval in milliseconds.
 */
void ares_telemetry_set_interval(uint32_t interval_ms);

#ifdef __cplusplus
}
#endif

#endif // ARES_TELEMETRY_H
