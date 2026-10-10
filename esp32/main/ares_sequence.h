#ifndef ARES_SEQUENCE_H
#define ARES_SEQUENCE_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Initialize sequence counter subsystem.
 */
void ares_sequence_init(void);

/**
 * Get next outbound sequence number (strictly monotonic).
 */
uint64_t ares_sequence_next_tx(void);

/**
 * Validate incoming sequence number against last seen value.
 * Rejects if seq <= last_rx_sequence.
 * Returns true if valid and updates last_rx_sequence.
 */
bool ares_sequence_validate_rx(uint64_t seq);

/**
 * Get current last received sequence number.
 */
uint64_t ares_sequence_get_last_rx(void);

/**
 * Reset sequence numbers (only permitted upon approved session renegotiation).
 */
void ares_sequence_reset(void);

#ifdef __cplusplus
}
#endif

#endif // ARES_SEQUENCE_H
