#ifndef ARES_COMMANDS_H
#define ARES_COMMANDS_H

#include <stdbool.h>
#include "esp_err.h"
#include "ares_protocol.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Initialize command dispatcher subsystem.
 */
void ares_commands_init(void);

/**
 * Dispatch and execute validated incoming ARES command.
 * Returns ESP_OK if command was recognized and handled.
 */
esp_err_t ares_commands_dispatch(const ares_envelope_t *envelope);

/**
 * High-priority STOP handler.
 * Halts active scans, cancels workers, and returns device to READY.
 */
void ares_commands_execute_stop(const char *reason, const char *orig_msg_id);

#ifdef __cplusplus
}
#endif

#endif // ARES_COMMANDS_H
