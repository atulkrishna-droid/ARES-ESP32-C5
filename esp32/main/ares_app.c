#include "ares_app.h"
#include "ares_logging.h"
#include "ares_secure_storage.h"
#include "ares_device.h"
#include "ares_capabilities.h"
#include "ares_sequence.h"
#include "ares_clock.h"
#include "ares_auth.h"
#include "ares_protocol.h"
#include "ares_commands.h"
#include "ares_transport_usb.h"
#include "ares_telemetry.h"
#include "ares_wifi.h"
#include "ares_ble.h"
#include "ares_802154.h"
#include "ares_storage.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include <string.h>
#include <stdlib.h>

#define ARES_FRAME_QUEUE_LEN 16

static ares_state_t s_app_state = ARES_STATE_BOOTING;
static QueueHandle_t s_rx_frame_queue = NULL;

const char* ares_app_state_to_str(ares_state_t state)
{
    switch (state) {
        case ARES_STATE_BOOTING: return "BOOTING";
        case ARES_STATE_INITIALIZING: return "INITIALIZING";
        case ARES_STATE_UNPAIRED: return "UNPAIRED";
        case ARES_STATE_PAIRING: return "PAIRING";
        case ARES_STATE_AUTHENTICATING: return "AUTHENTICATING";
        case ARES_STATE_READY: return "READY";
        case ARES_STATE_BUSY: return "BUSY";
        case ARES_STATE_ERROR: return "ERROR";
        case ARES_STATE_STOPPING: return "STOPPING";
        case ARES_STATE_UPDATING: return "UPDATING";
        default: return "UNKNOWN";
    }
}

void ares_app_set_state(ares_state_t state)
{
    if (s_app_state != state) {
        ARES_LOGI("State transition: %s -> %s",
                  ares_app_state_to_str(s_app_state), ares_app_state_to_str(state));
        s_app_state = state;
    }
}

ares_state_t ares_app_get_state(void)
{
    return s_app_state;
}

bool ares_app_can_execute_commands(void)
{
    return (s_app_state == ARES_STATE_READY || s_app_state == ARES_STATE_BUSY);
}

static void ares_protocol_task(void *pvParameters)
{
    ARES_LOGI("ARES Protocol processing task active");
    char *frame_str = NULL;

    while (1) {
        if (xQueueReceive(s_rx_frame_queue, &frame_str, portMAX_DELAY) == pdTRUE) {
            if (frame_str != NULL) {
                ares_envelope_t envelope;
                const char *err_code = NULL;
                const char *err_msg = NULL;

                esp_err_t err = ares_protocol_parse_and_validate(frame_str, &envelope, &err_code, &err_msg);
                if (err == ESP_OK) {
                    // Check if command is STOP (always executable even in busy state)
                    if (strcmp(envelope.type, ARES_TYPE_STOP) == 0) {
                        ares_commands_execute_stop("REMOTE_REQUEST", envelope.message_id);
                    } else if (!ares_app_can_execute_commands()) {
                        // State guard check
                        char *resp = ares_protocol_create_error_response(
                            ARES_ERR_UNAUTHORIZED, "Device not in executable state", envelope.message_id);
                        if (resp) {
                            ares_transport_usb_send_frame(resp);
                            free(resp);
                        }
                    } else {
                        // Dispatch to commands engine
                        ares_commands_dispatch(&envelope);
                    }
                    ares_protocol_free_envelope(&envelope);
                } else {
                    ARES_LOGW("Frame validation failed: %s (%s)", err_code ? err_code : "ERR", err_msg ? err_msg : "");
                    char *err_resp = ares_protocol_create_error_response(err_code, err_msg, NULL);
                    if (err_resp != NULL) {
                        ares_transport_usb_send_frame(err_resp);
                        free(err_resp);
                    }
                }

                free(frame_str);
                frame_str = NULL;
            }
        }
    }
}

esp_err_t ares_app_start(void)
{
    ares_app_set_state(ARES_STATE_BOOTING);

    // 1. Initialize Logging
    ares_logging_init();
    ARES_LOGI("=================================================");
    ARES_LOGI("ARES FIRMWARE V%s BOOTING", ARES_FIRMWARE_VERSION);
    ARES_LOGI("Target: %s (%s)", ARES_BOARD_TARGET, ARES_CHIP_TARGET);
    ARES_LOGI("=================================================");

    ares_app_set_state(ARES_STATE_INITIALIZING);

    // 2. Initialize NVS & Secure Storage
    ares_secure_storage_initialize();

    // 3. Initialize Device Identity & Hardware Probing
    ares_device_init();

    // 4. Initialize Hardware Capabilities Discovery
    ares_capabilities_init();

    // 5. Initialize Sequence & Clock Subsystems
    ares_sequence_init();
    ares_clock_init();

    // 6. Initialize Cryptographic Auth Subsystem
    ares_auth_init();

    // 7. Initialize Radios & Peripherals
    ares_wifi_init();
    ares_ble_init();
    ares_802154_init();
    ares_storage_init();

    // 8. Create FreeRTOS Protocol Dispatch Queue & Task
    s_rx_frame_queue = xQueueCreate(ARES_FRAME_QUEUE_LEN, sizeof(char *));
    xTaskCreate(ares_protocol_task, "ares_proto_task", 6144, NULL, configMAX_PRIORITIES - 3, NULL);

    // 9. Initialize USB Hardware Transport
    ares_transport_usb_init(s_rx_frame_queue);

    // 10. Initialize Command Dispatcher
    ares_commands_init();

    // 11. Start Periodic Telemetry
    ares_telemetry_init();

    // 12. Transition to READY
    ares_app_set_state(ARES_STATE_READY);
    ARES_LOGI("ARES Device %s entered state: READY", ares_device_get_id());

    // 13. Send Initial HELLO Announce Message over USB
    cJSON *hello_payload = cJSON_CreateObject();
    cJSON_AddStringToObject(hello_payload, "protocol_version", ARES_PROTOCOL_VERSION);
    cJSON_AddStringToObject(hello_payload, "firmware_version", ARES_FIRMWARE_VERSION);
    cJSON_AddStringToObject(hello_payload, "device_id", ares_device_get_id());
    cJSON_AddStringToObject(hello_payload, "board_target", ARES_BOARD_TARGET);
    cJSON_AddStringToObject(hello_payload, "status", "READY");

    char *hello_frame = ares_protocol_create_message(ARES_TYPE_HELLO, hello_payload);
    if (hello_frame != NULL) {
        ares_transport_usb_send_frame(hello_frame);
        free(hello_frame);
        ARES_LOGI("Initial HELLO handshake dispatched over USB");
    }

    return ESP_OK;
}
