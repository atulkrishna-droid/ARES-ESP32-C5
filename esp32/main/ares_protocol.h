#ifndef ARES_PROTOCOL_H
#define ARES_PROTOCOL_H

#include <stdint.h>
#include <stdbool.h>
#include "cJSON.h"
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ARES_PROTOCOL_NAME "ARES/1.0"
#define ARES_MAX_PAYLOAD_SIZE 65536 // 64KB on microcontroller

// Protocol Message Types
#define ARES_TYPE_HELLO              "HELLO"
#define ARES_TYPE_DEVICE_INFO        "DEVICE_INFO"
#define ARES_TYPE_CAPABILITIES       "CAPABILITIES"
#define ARES_TYPE_HEARTBEAT          "HEARTBEAT"
#define ARES_TYPE_TELEMETRY          "TELEMETRY"
#define ARES_TYPE_STATUS             "STATUS"
#define ARES_TYPE_WIFI_SCAN_START    "WIFI_SCAN_START"
#define ARES_TYPE_WIFI_SCAN_STOP     "WIFI_SCAN_STOP"
#define ARES_TYPE_WIFI_SCAN_RESULT   "WIFI_SCAN_RESULT"
#define ARES_TYPE_WIFI_SCAN_COMPLETE "WIFI_SCAN_COMPLETE"
#define ARES_TYPE_BLE_SCAN_START     "BLE_SCAN_START"
#define ARES_TYPE_BLE_SCAN_STOP      "BLE_SCAN_STOP"
#define ARES_TYPE_BLE_SCAN_RESULT    "BLE_SCAN_RESULT"
#define ARES_TYPE_BLE_SCAN_COMPLETE  "BLE_SCAN_COMPLETE"
#define ARES_TYPE_STOP               "STOP"
#define ARES_TYPE_STOPPED            "STOPPED"
#define ARES_TYPE_ACK                "ACK"
#define ARES_TYPE_ERROR              "ERROR"

// Standard Error Codes
#define ARES_ERR_INVALID_MESSAGE     "INVALID_MESSAGE"
#define ARES_ERR_INVALID_PROTOCOL    "INVALID_PROTOCOL"
#define ARES_ERR_INVALID_DEVICE      "INVALID_DEVICE"
#define ARES_ERR_INVALID_SIGNATURE   "INVALID_SIGNATURE"
#define ARES_ERR_INVALID_SEQUENCE    "INVALID_SEQUENCE"
#define ARES_ERR_TIMESTAMP_EXPIRED   "TIMESTAMP_EXPIRED"
#define ARES_ERR_UNAUTHORIZED        "UNAUTHORIZED"
#define ARES_ERR_BUSY                "BUSY"
#define ARES_ERR_NOT_SUPPORTED       "NOT_SUPPORTED"
#define ARES_ERR_HARDWARE_ERROR      "HARDWARE_ERROR"
#define ARES_ERR_STORAGE_ERROR       "STORAGE_ERROR"
#define ARES_ERR_WIFI_ERROR          "WIFI_ERROR"
#define ARES_ERR_BLE_ERROR           "BLE_ERROR"
#define ARES_ERR_INTERNAL_ERROR      "INTERNAL_ERROR"

typedef struct {
    char protocol[16];
    char message_id[48];
    char device_id[48];
    char timestamp[32];
    char type[32];
    uint64_t sequence;
    cJSON *payload;
    char signature[68];
    char *raw_payload_json;
} ares_envelope_t;

/**
 * Initialize protocol subsystem.
 */
void ares_protocol_init(void);

/**
 * Parse and validate incoming raw JSON frame into an ares_envelope_t.
 * Validates protocol name, message type whitelist, device id, sequence replay, timestamp, signature.
 * Returns ESP_OK if fully valid, or an error code.
 * If rejected, error_code_out and error_msg_out are filled.
 */
esp_err_t ares_protocol_parse_and_validate(
    const char *json_str,
    ares_envelope_t *out_envelope,
    const char **error_code_out,
    const char **error_msg_out
);

/**
 * Free resources allocated inside an ares_envelope_t.
 */
void ares_protocol_free_envelope(ares_envelope_t *envelope);

/**
 * Create and sign a complete outbound ARES/1.0 envelope.
 * Returns newly allocated JSON string (caller must free with free()).
 */
char* ares_protocol_create_message(const char *type, cJSON *payload);

/**
 * Create a standard error response string (caller must free()).
 */
char* ares_protocol_create_error_response(const char *code, const char *message, const char *orig_msg_id);

/**
 * Create a standard ACK response string (caller must free()).
 */
char* ares_protocol_create_ack_response(const char *orig_msg_id);

/**
 * Check if a command is in the authorized command whitelist.
 */
bool ares_protocol_is_whitelisted_command(const char *type);

#ifdef __cplusplus
}
#endif

#endif // ARES_PROTOCOL_H
