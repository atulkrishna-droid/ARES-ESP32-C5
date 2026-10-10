#include "ares_commands.h"
#include "ares_protocol.h"
#include "ares_device.h"
#include "ares_capabilities.h"
#include "ares_telemetry.h"
#include "ares_wifi.h"
#include "ares_ble.h"
#include "ares_storage.h"
#include "ares_transport_usb.h"
#include "ares_logging.h"
#include <string.h>
#include <stdlib.h>

void ares_commands_init(void)
{
    ARES_LOGI("Command dispatcher initialized (Strict whitelist enforcement)");
}

void ares_commands_execute_stop(const char *reason, const char *orig_msg_id)
{
    ARES_LOGW("High-priority STOP received: %s", reason ? reason : "UNSPECIFIED");

    // Abort Wi-Fi and BLE operations immediately
    ares_wifi_stop_scan();
    ares_ble_stop_scan();

    cJSON *payload = cJSON_CreateObject();
    cJSON_AddStringToObject(payload, "status", "STOPPED");
    cJSON_AddStringToObject(payload, "reason", reason ? reason : "REMOTE_REQUEST");
    if (orig_msg_id) {
        cJSON_AddStringToObject(payload, "in_reply_to", orig_msg_id);
    }

    char *msg = ares_protocol_create_message(ARES_TYPE_STOPPED, payload);
    if (msg != NULL) {
        ares_transport_usb_send_frame(msg);
        free(msg);
    }
}

esp_err_t ares_commands_dispatch(const ares_envelope_t *envelope)
{
    if (envelope == NULL) return ESP_ERR_INVALID_ARG;

    const char *type = envelope->type;
    ARES_LOGI("Dispatching command: %s (Seq: %llu)", type, (unsigned long long)envelope->sequence);

    // 1. HELLO Handshake
    if (strcmp(type, ARES_TYPE_HELLO) == 0) {
        cJSON *payload = cJSON_CreateObject();
        cJSON_AddStringToObject(payload, "protocol_version", ARES_PROTOCOL_VERSION);
        cJSON_AddStringToObject(payload, "firmware_version", ARES_FIRMWARE_VERSION);
        cJSON_AddStringToObject(payload, "device_id", ares_device_get_id());
        cJSON_AddStringToObject(payload, "status", "READY");

        char *resp = ares_protocol_create_message(ARES_TYPE_HELLO, payload);
        if (resp != NULL) {
            ares_transport_usb_send_frame(resp);
            free(resp);
        }
        return ESP_OK;
    }

    // 2. DEVICE_INFO
    if (strcmp(type, ARES_TYPE_DEVICE_INFO) == 0) {
        cJSON *payload = cJSON_CreateObject();
        ares_device_populate_json(payload);

        char *resp = ares_protocol_create_message(ARES_TYPE_DEVICE_INFO, payload);
        if (resp != NULL) {
            ares_transport_usb_send_frame(resp);
            free(resp);
        }
        return ESP_OK;
    }

    // 3. CAPABILITIES Discovery
    if (strcmp(type, ARES_TYPE_CAPABILITIES) == 0) {
        cJSON *payload = cJSON_CreateObject();
        ares_capabilities_populate_json(payload);

        char *resp = ares_protocol_create_message(ARES_TYPE_CAPABILITIES, payload);
        if (resp != NULL) {
            ares_transport_usb_send_frame(resp);
            free(resp);
        }
        return ESP_OK;
    }

    // 4. HEARTBEAT / GET_TELEMETRY
    if (strcmp(type, ARES_TYPE_HEARTBEAT) == 0 ||
        strcmp(type, "GET_TELEMETRY") == 0) {
        return ares_telemetry_send_heartbeat();
    }

    // 5. GET_STATUS
    if (strcmp(type, ARES_TYPE_STATUS) == 0 ||
        strcmp(type, "GET_STATUS") == 0) {
        cJSON *payload = cJSON_CreateObject();
        bool is_busy = (ares_wifi_get_status() == ARES_WIFI_STATE_SCANNING ||
                        ares_ble_get_status() == ARES_BLE_STATE_SCANNING);
        cJSON_AddStringToObject(payload, "state", is_busy ? "BUSY" : "READY");
        cJSON_AddStringToObject(payload, "wifi_state", ares_wifi_state_to_str(ares_wifi_get_status()));
        cJSON_AddStringToObject(payload, "ble_state", ares_ble_state_to_str(ares_ble_get_status()));

        char *resp = ares_protocol_create_message(ARES_TYPE_STATUS, payload);
        if (resp != NULL) {
            ares_transport_usb_send_frame(resp);
            free(resp);
        }
        return ESP_OK;
    }

    // 6. GET_STORAGE_STATUS
    if (strcmp(type, "GET_STORAGE_STATUS") == 0) {
        cJSON *payload = cJSON_CreateObject();
        cJSON_AddStringToObject(payload, "storage_state", ares_storage_state_to_str(ares_storage_get_state()));
        cJSON_AddNumberToObject(payload, "capacity_bytes", (double)ares_storage_get_capacity());
        cJSON_AddNumberToObject(payload, "free_bytes", (double)ares_storage_get_free_space());

        char *resp = ares_protocol_create_message("STORAGE_STATUS", payload);
        if (resp != NULL) {
            ares_transport_usb_send_frame(resp);
            free(resp);
        }
        return ESP_OK;
    }

    // 7. WIFI_SCAN_START
    if (strcmp(type, ARES_TYPE_WIFI_SCAN_START) == 0) {
        uint16_t dwell = 120;
        const char *band = "ALL";
        if (envelope->payload != NULL) {
            cJSON *dw = cJSON_GetObjectItemCaseSensitive(envelope->payload, "dwell_time_ms");
            if (cJSON_IsNumber(dw)) dwell = (uint16_t)dw->valueint;
            cJSON *bf = cJSON_GetObjectItemCaseSensitive(envelope->payload, "band");
            if (cJSON_IsString(bf)) band = bf->valuestring;
        }

        esp_err_t err = ares_wifi_start_scan(dwell, band);
        if (err == ESP_OK) {
            char *ack = ares_protocol_create_ack_response(envelope->message_id);
            if (ack != NULL) {
                ares_transport_usb_send_frame(ack);
                free(ack);
            }
        } else {
            char *err_resp = ares_protocol_create_error_response(ARES_ERR_BUSY, "Wi-Fi scan already active", envelope->message_id);
            if (err_resp != NULL) {
                ares_transport_usb_send_frame(err_resp);
                free(err_resp);
            }
        }
        return err;
    }

    // 8. WIFI_SCAN_STOP
    if (strcmp(type, ARES_TYPE_WIFI_SCAN_STOP) == 0) {
        ares_wifi_stop_scan();
        char *ack = ares_protocol_create_ack_response(envelope->message_id);
        if (ack != NULL) {
            ares_transport_usb_send_frame(ack);
            free(ack);
        }
        return ESP_OK;
    }

    // 9. BLE_SCAN_START
    if (strcmp(type, ARES_TYPE_BLE_SCAN_START) == 0) {
        uint16_t duration = 5;
        if (envelope->payload != NULL) {
            cJSON *dur = cJSON_GetObjectItemCaseSensitive(envelope->payload, "duration_sec");
            if (cJSON_IsNumber(dur)) duration = (uint16_t)dur->valueint;
        }
        esp_err_t err = ares_ble_start_scan(duration);
        if (err == ESP_OK) {
            char *ack = ares_protocol_create_ack_response(envelope->message_id);
            if (ack != NULL) {
                ares_transport_usb_send_frame(ack);
                free(ack);
            }
        } else {
            char *err_resp = ares_protocol_create_error_response(ARES_ERR_BUSY, "BLE scan already active", envelope->message_id);
            if (err_resp != NULL) {
                ares_transport_usb_send_frame(err_resp);
                free(err_resp);
            }
        }
        return err;
    }

    // 10. BLE_SCAN_STOP
    if (strcmp(type, ARES_TYPE_BLE_SCAN_STOP) == 0) {
        ares_ble_stop_scan();
        char *ack = ares_protocol_create_ack_response(envelope->message_id);
        if (ack != NULL) {
            ares_transport_usb_send_frame(ack);
            free(ack);
        }
        return ESP_OK;
    }

    // 11. STOP Safety Command
    if (strcmp(type, ARES_TYPE_STOP) == 0) {
        ares_commands_execute_stop("REMOTE_REQUEST", envelope->message_id);
        return ESP_OK;
    }

    // Rejected command
    ARES_LOGW("Rejected unauthorized command: %s", type);
    char *err_resp = ares_protocol_create_error_response(ARES_ERR_NOT_SUPPORTED, "Command rejected", envelope->message_id);
    if (err_resp != NULL) {
        ares_transport_usb_send_frame(err_resp);
        free(err_resp);
    }
    return ESP_ERR_NOT_SUPPORTED;
}
