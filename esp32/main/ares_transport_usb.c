#include "ares_transport_usb.h"
#include "ares_logging.h"
#include "driver/usb_serial_jtag.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include <string.h>
#include <stdlib.h>

static QueueHandle_t s_rx_queue = NULL;
static SemaphoreHandle_t s_tx_mutex = NULL;
static bool s_is_connected = false;

static void usb_rx_task(void *pvParameters)
{
    uint8_t rx_byte_buf[256];
    char line_buf[ARES_USB_MAX_FRAME_LEN];
    size_t line_pos = 0;

    ARES_LOGI("USB transport RX task running");

    while (1) {
        int len = usb_serial_jtag_read_bytes(rx_byte_buf, sizeof(rx_byte_buf), pdMS_TO_TICKS(50));
        if (len > 0) {
            s_is_connected = true;
            for (int i = 0; i < len; i++) {
                char c = (char)rx_byte_buf[i];
                if (c == '\n' || c == '\r') {
                    if (line_pos > 0) {
                        line_buf[line_pos] = '\0';
                        char *frame = strdup(line_buf);
                        if (frame != NULL) {
                            if (xQueueSend(s_rx_queue, &frame, pdMS_TO_TICKS(100)) != pdTRUE) {
                                ARES_LOGW("USB RX queue full, frame dropped");
                                free(frame);
                            }
                        }
                        line_pos = 0;
                    }
                } else {
                    if (line_pos < sizeof(line_buf) - 1) {
                        line_buf[line_pos++] = c;
                    } else {
                        // Frame exceeded maximum size, discard
                        ARES_LOGW("Frame exceeded max size (%d), buffer cleared", ARES_USB_MAX_FRAME_LEN);
                        line_pos = 0;
                    }
                }
            }
        } else {
            // Heartbeat/idle check
            vTaskDelay(pdMS_TO_TICKS(10));
        }
    }
}

esp_err_t ares_transport_usb_init(QueueHandle_t rx_frame_queue)
{
    s_rx_queue = rx_frame_queue;
    if (s_tx_mutex == NULL) {
        s_tx_mutex = xSemaphoreCreateMutex();
    }

    usb_serial_jtag_driver_config_t usb_config = {
        .rx_buffer_size = ARES_USB_RX_BUF_SIZE,
        .tx_buffer_size = ARES_USB_RX_BUF_SIZE,
    };

    esp_err_t err = usb_serial_jtag_driver_install(&usb_config);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ARES_LOGE("Failed to install USB Serial/JTAG driver: 0x%x", err);
        return err;
    }

    s_is_connected = true;

    // Spawn high-priority RX task
    xTaskCreate(usb_rx_task, "ares_usb_rx", 4096, NULL, configMAX_PRIORITIES - 2, NULL);

    ARES_LOGI("USB Serial/JTAG transport initialized");
    return ESP_OK;
}

esp_err_t ares_transport_usb_send(const char *data, size_t len)
{
    if (data == NULL || len == 0) return ESP_ERR_INVALID_ARG;

    if (s_tx_mutex != NULL) {
        xSemaphoreTake(s_tx_mutex, portMAX_DELAY);
    }

    int written = usb_serial_jtag_write_bytes(data, len, pdMS_TO_TICKS(500));

    if (s_tx_mutex != NULL) {
        xSemaphoreGive(s_tx_mutex);
    }

    return (written == (int)len) ? ESP_OK : ESP_FAIL;
}

esp_err_t ares_transport_usb_send_frame(const char *json_str)
{
    if (json_str == NULL) return ESP_ERR_INVALID_ARG;

    size_t len = strlen(json_str);
    esp_err_t err = ares_transport_usb_send(json_str, len);
    if (err == ESP_OK) {
        err = ares_transport_usb_send("\n", 1);
    }
    return err;
}

bool ares_transport_usb_is_connected(void)
{
    return s_is_connected;
}
