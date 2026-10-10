#ifndef ARES_TRANSPORT_USB_H
#define ARES_TRANSPORT_USB_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ARES_USB_RX_BUF_SIZE 4096
#define ARES_USB_MAX_FRAME_LEN 8192

/**
 * Initialize USB Serial/JTAG hardware transport.
 * Completed frames are pushed to rx_frame_queue as dynamically allocated strings.
 */
esp_err_t ares_transport_usb_init(QueueHandle_t rx_frame_queue);

/**
 * Send raw buffer over USB channel.
 */
esp_err_t ares_transport_usb_send(const char *data, size_t len);

/**
 * Send null-terminated JSON frame with newline delimiter '\n'.
 */
esp_err_t ares_transport_usb_send_frame(const char *json_str);

/**
 * Returns true if USB host connection is detected.
 */
bool ares_transport_usb_is_connected(void);

#ifdef __cplusplus
}
#endif

#endif // ARES_TRANSPORT_USB_H
