#ifndef ARES_CLOCK_H
#define ARES_CLOCK_H

#include <stdint.h>
#include <stdbool.h>
#include <time.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ARES_MAX_CLOCK_SKEW_SEC 60

/**
 * Initialize clock subsystem.
 */
void ares_clock_init(void);

/**
 * Format current UTC time as ISO 8601 string: YYYY-MM-DDTHH:MM:SSZ
 */
void ares_clock_get_iso8601(char *buf, size_t buf_len);

/**
 * Parse an ISO 8601 UTC timestamp string to epoch seconds.
 * Returns true on success.
 */
bool ares_clock_parse_iso8601(const char *iso_str, time_t *out_time);

/**
 * Validate incoming timestamp against clock skew window (+-60s).
 */
bool ares_clock_validate_skew(const char *iso_str);

/**
 * Synchronize system clock to authoritative backend epoch seconds.
 */
void ares_clock_sync(time_t epoch_sec);

/**
 * Check if the system clock has been synchronized.
 */
bool ares_clock_is_synchronized(void);

#ifdef __cplusplus
}
#endif

#endif // ARES_CLOCK_H
