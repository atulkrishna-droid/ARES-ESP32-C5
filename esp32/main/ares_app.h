#ifndef ARES_APP_H
#define ARES_APP_H

#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    ARES_STATE_BOOTING = 0,
    ARES_STATE_INITIALIZING,
    ARES_STATE_UNPAIRED,
    ARES_STATE_PAIRING,
    ARES_STATE_AUTHENTICATING,
    ARES_STATE_READY,
    ARES_STATE_BUSY,
    ARES_STATE_ERROR,
    ARES_STATE_STOPPING,
    ARES_STATE_UPDATING
} ares_state_t;

/**
 * Initialize core application, start FreeRTOS tasks, and execute boot sequence.
 */
esp_err_t ares_app_start(void);

/**
 * Transition application state machine to target state.
 */
void ares_app_set_state(ares_state_t state);

/**
 * Get current application state.
 */
ares_state_t ares_app_get_state(void);

/**
 * State string representation.
 */
const char* ares_app_state_to_str(ares_state_t state);

/**
 * Check if the device is permitted to accept active assessment commands.
 */
bool ares_app_can_execute_commands(void);

#ifdef __cplusplus
}
#endif

#endif // ARES_APP_H
