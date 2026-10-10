#include "ares_protocol.h"
#include "ares_auth.h"
#include "ares_sequence.h"
#include "ares_clock.h"
#include "ares_device.h"
#include "ares_logging.h"
#include "esp_random.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

void ares_protocol_init(void)
{
    ARES_LOGI("Protocol engine initialized (%s)", ARES_PROTOCOL_NAME);
}

bool ares_protocol_is_whitelisted_command(const char *type)
{
    if (type == NULL) return false;
    static const char *whitelist[] = {
        ARES_TYPE_HELLO,
        ARES_TYPE_DEVICE_INFO,
        ARES_TYPE_CAPABILITIES,
        ARES_TYPE_HEARTBEAT,
        ARES_TYPE_TELEMETRY,
        ARES_TYPE_STATUS,
        "GET_STATUS",
        "GET_TELEMETRY",
        "GET_STORAGE_STATUS",
        ARES_TYPE_WIFI_SCAN_START,
        ARES_TYPE_WIFI_SCAN_STOP,
        ARES_TYPE_BLE_SCAN_START,
        ARES_TYPE_BLE_SCAN_STOP,
        ARES_TYPE_STOP,
        ARES_TYPE_ACK,
        NULL
    };
    for (int i = 0; whitelist[i] != NULL; i++) {
        if (strcmp(type, whitelist[i]) == 0) {
            return true;
        }
    }
    return false;
}

esp_err_t ares_protocol_parse_and_validate(
    const char *json_str,
    ares_envelope_t *out_envelope,
    const char **error_code_out,
    const char **error_msg_out
) {
    if (json_str == NULL || out_envelope == NULL) {
        if (error_code_out) *error_code_out = ARES_ERR_INVALID_MESSAGE;
        if (error_msg_out) *error_msg_out = "Null message buffer";
        return ESP_ERR_INVALID_ARG;
    }

    memset(out_envelope, 0, sizeof(ares_envelope_t));

    // 1. Validate JSON
    cJSON *root = cJSON_Parse(json_str);
    if (root == NULL) {
        if (error_code_out) *error_code_out = ARES_ERR_INVALID_MESSAGE;
        if (error_msg_out) *error_msg_out = "Malformed JSON syntax";
        return ESP_ERR_INVALID_ARG;
    }

    // 2. Validate Protocol Version
    cJSON *proto_item = cJSON_GetObjectItemCaseSensitive(root, "protocol");
    if (!cJSON_IsString(proto_item) || strcmp(proto_item->valuestring, ARES_PROTOCOL_NAME) != 0) {
        cJSON_Delete(root);
        if (error_code_out) *error_code_out = ARES_ERR_INVALID_PROTOCOL;
        if (error_msg_out) *error_msg_out = "Unsupported protocol version";
        return ESP_ERR_NOT_SUPPORTED;
    }
    strncpy(out_envelope->protocol, proto_item->valuestring, sizeof(out_envelope->protocol) - 1);

    // 3. Message Type & Whitelist
    cJSON *type_item = cJSON_GetObjectItemCaseSensitive(root, "type");
    if (!cJSON_IsString(type_item)) {
        cJSON_Delete(root);
        if (error_code_out) *error_code_out = ARES_ERR_INVALID_MESSAGE;
        if (error_msg_out) *error_msg_out = "Missing message type";
        return ESP_ERR_INVALID_ARG;
    }
    if (!ares_protocol_is_whitelisted_command(type_item->valuestring)) {
        cJSON_Delete(root);
        if (error_code_out) *error_code_out = ARES_ERR_NOT_SUPPORTED;
        if (error_msg_out) *error_msg_out = "Command not in authorized whitelist";
        return ESP_ERR_NOT_SUPPORTED;
    }
    strncpy(out_envelope->type, type_item->valuestring, sizeof(out_envelope->type) - 1);

    // 4. Message ID
    cJSON *mid_item = cJSON_GetObjectItemCaseSensitive(root, "message_id");
    if (cJSON_IsString(mid_item)) {
        strncpy(out_envelope->message_id, mid_item->valuestring, sizeof(out_envelope->message_id) - 1);
    }

    // 5. Device ID Check
    cJSON *dev_item = cJSON_GetObjectItemCaseSensitive(root, "device_id");
    if (cJSON_IsString(dev_item)) {
        const char *my_id = ares_device_get_id();
        // Allow broadcast/unassigned in HELLO initial phase, or require matching device_id
        if (strcmp(out_envelope->type, ARES_TYPE_HELLO) != 0 &&
            strcmp(dev_item->valuestring, "*") != 0 &&
            strcmp(dev_item->valuestring, my_id) != 0) {
            cJSON_Delete(root);
            if (error_code_out) *error_code_out = ARES_ERR_INVALID_DEVICE;
            if (error_msg_out) *error_msg_out = "Target device ID mismatch";
            return ESP_ERR_INVALID_STATE;
        }
        strncpy(out_envelope->device_id, dev_item->valuestring, sizeof(out_envelope->device_id) - 1);
    }

    // 6. Timestamp & Clock Skew Validation
    cJSON *ts_item = cJSON_GetObjectItemCaseSensitive(root, "timestamp");
    if (!cJSON_IsString(ts_item) || !ares_clock_validate_skew(ts_item->valuestring)) {
        cJSON_Delete(root);
        if (error_code_out) *error_code_out = ARES_ERR_TIMESTAMP_EXPIRED;
        if (error_msg_out) *error_msg_out = "Timestamp expired or clock skew out of bounds";
        return ESP_ERR_TIMEOUT;
    }
    strncpy(out_envelope->timestamp, ts_item->valuestring, sizeof(out_envelope->timestamp) - 1);

    // 7. Sequence Replay Protection
    cJSON *seq_item = cJSON_GetObjectItemCaseSensitive(root, "sequence");
    if (!cJSON_IsNumber(seq_item)) {
        cJSON_Delete(root);
        if (error_code_out) *error_code_out = ARES_ERR_INVALID_SEQUENCE;
        if (error_msg_out) *error_msg_out = "Missing sequence counter";
        return ESP_ERR_INVALID_ARG;
    }
    uint64_t seq = (uint64_t)seq_item->valuedouble;
    if (!ares_sequence_validate_rx(seq)) {
        cJSON_Delete(root);
        if (error_code_out) *error_code_out = ARES_ERR_INVALID_SEQUENCE;
        if (error_msg_out) *error_msg_out = "Replay rejected: sequence counter stale";
        return ESP_ERR_INVALID_STATE;
    }
    out_envelope->sequence = seq;

    // 8. Payload & Signature
    cJSON *payload_item = cJSON_GetObjectItemCaseSensitive(root, "payload");
    char *payload_str = NULL;
    if (payload_item != NULL) {
        payload_str = cJSON_PrintUnformatted(payload_item);
    } else {
        payload_str = strdup("{}");
    }

    cJSON *sig_item = cJSON_GetObjectItemCaseSensitive(root, "signature");
    if (sig_item && cJSON_IsString(sig_item)) {
        if (!ares_auth_verify_signature(out_envelope->protocol, out_envelope->type,
                                        out_envelope->device_id, out_envelope->timestamp,
                                        out_envelope->sequence, payload_str, sig_item->valuestring)) {
            free(payload_str);
            cJSON_Delete(root);
            if (error_code_out) *error_code_out = ARES_ERR_INVALID_SIGNATURE;
            if (error_msg_out) *error_msg_out = "Cryptographic signature verification failed";
            return ESP_ERR_INVALID_CRC;
        }
        strncpy(out_envelope->signature, sig_item->valuestring, sizeof(out_envelope->signature) - 1);
    }

    out_envelope->raw_payload_json = payload_str;
    out_envelope->payload = root; // Keep root alive to preserve payload pointer references

    return ESP_OK;
}

void ares_protocol_free_envelope(ares_envelope_t *envelope)
{
    if (envelope == NULL) return;
    if (envelope->raw_payload_json != NULL) {
        free(envelope->raw_payload_json);
        envelope->raw_payload_json = NULL;
    }
    if (envelope->payload != NULL) {
        cJSON_Delete(envelope->payload);
        envelope->payload = NULL;
    }
}

char* ares_protocol_create_message(const char *type, cJSON *payload)
{
    if (type == NULL) return NULL;

    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "protocol", ARES_PROTOCOL_NAME);

    // Random message ID
    char mid[32];
    snprintf(mid, sizeof(mid), "msg-%08lx", (unsigned long)esp_random());
    cJSON_AddStringToObject(root, "message_id", mid);

    // Device identity
    cJSON_AddStringToObject(root, "device_id", ares_device_get_id());

    // Timestamp
    char ts[32];
    ares_clock_get_iso8601(ts, sizeof(ts));
    cJSON_AddStringToObject(root, "timestamp", ts);

    // Type & Sequence
    cJSON_AddStringToObject(root, "type", type);
    uint64_t seq = ares_sequence_next_tx();
    cJSON_AddNumberToObject(root, "sequence", (double)seq);

    // Attach Payload
    cJSON *p = payload ? payload : cJSON_CreateObject();
    cJSON_AddItemToObject(root, "payload", p);

    // Compute canonical JSON string for signature
    char *payload_str = cJSON_PrintUnformatted(p);

    char sig_hex[ARES_SIGNATURE_HEX_LEN + 1];
    if (ares_auth_compute_signature(ARES_PROTOCOL_NAME, type, ares_device_get_id(),
                                    ts, seq, payload_str, sig_hex, sizeof(sig_hex)) == ESP_OK) {
        cJSON_AddStringToObject(root, "signature", sig_hex);
    } else {
        cJSON_AddStringToObject(root, "signature", "");
    }
    free(payload_str);

    char *out_json = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    return out_json;
}

char* ares_protocol_create_error_response(const char *code, const char *message, const char *orig_msg_id)
{
    cJSON *payload = cJSON_CreateObject();
    cJSON_AddStringToObject(payload, "code", code ? code : ARES_ERR_INTERNAL_ERROR);
    cJSON_AddStringToObject(payload, "message", message ? message : "Operation failed");
    if (orig_msg_id) {
        cJSON_AddStringToObject(payload, "in_reply_to", orig_msg_id);
    }
    return ares_protocol_create_message(ARES_TYPE_ERROR, payload);
}

char* ares_protocol_create_ack_response(const char *orig_msg_id)
{
    cJSON *payload = cJSON_CreateObject();
    cJSON_AddStringToObject(payload, "status", "SUCCESS");
    if (orig_msg_id) {
        cJSON_AddStringToObject(payload, "in_reply_to", orig_msg_id);
    }
    return ares_protocol_create_message(ARES_TYPE_ACK, payload);
}
