#ifndef ARES_STORAGE_H
#define ARES_STORAGE_H

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    ARES_STORAGE_NOT_PRESENT = 0,
    ARES_STORAGE_MOUNTED,
    ARES_STORAGE_ERROR
} ares_storage_state_t;

/**
 * Initialize optional microSD storage subsystem (SPI mode).
 * Operates gracefully if card is missing.
 */
esp_err_t ares_storage_init(void);

/**
 * Probe card presence.
 */
bool ares_storage_detect_card(void);

/**
 * Get total capacity in bytes.
 */
uint64_t ares_storage_get_capacity(void);

/**
 * Get free capacity in bytes.
 */
uint64_t ares_storage_get_free_space(void);

/**
 * Write log entry to SD storage if mounted.
 */
esp_err_t ares_storage_write_log(const char *entry);

/**
 * Read latest log entries.
 */
esp_err_t ares_storage_read_log(char *buf, size_t max_len);

/**
 * Unmount and close storage.
 */
void ares_storage_close(void);

/**
 * Get current storage state.
 */
ares_storage_state_t ares_storage_get_state(void);

/**
 * State string for telemetry.
 */
const char* ares_storage_state_to_str(ares_storage_state_t state);

#ifdef __cplusplus
}
#endif

#endif // ARES_STORAGE_H
