#ifndef ARES_802154_H
#define ARES_802154_H

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    ARES_154_STATE_NOT_SUPPORTED = 0,
    ARES_154_STATE_IDLE,
    ARES_154_STATE_LISTENING,
    ARES_154_STATE_ERROR
} ares_154_state_t;

/**
 * Initialize IEEE 802.15.4 radio subsystem.
 */
esp_err_t ares_802154_init(void);

/**
 * Check if 802.15.4 radio is supported and ready.
 */
bool ares_802154_is_supported(void);

/**
 * Get current 802.15.4 state.
 */
ares_154_state_t ares_802154_get_state(void);

/**
 * Get state string for telemetry.
 */
const char* ares_802154_state_to_str(ares_154_state_t state);

#ifdef __cplusplus
}
#endif

#endif // ARES_802154_H
