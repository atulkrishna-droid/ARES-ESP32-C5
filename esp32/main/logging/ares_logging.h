#ifndef ARES_LOGGING_H
#define ARES_LOGGING_H

#include <stdio.h>
#include <stdarg.h>
#include "esp_log.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ARES_TAG "ARES"

/**
 * Initialize ARES secure logging subsystem.
 */
void ares_logging_init(void);

/**
 * ARES logging macros.
 * Note: Never pass sensitive tokens, HMAC keys, or private material into these macros.
 */
#define ARES_LOGE(format, ...) ESP_LOGE(ARES_TAG, format, ##__VA_ARGS__)
#define ARES_LOGW(format, ...) ESP_LOGW(ARES_TAG, format, ##__VA_ARGS__)
#define ARES_LOGI(format, ...) ESP_LOGI(ARES_TAG, format, ##__VA_ARGS__)
#define ARES_LOGD(format, ...) ESP_LOGD(ARES_TAG, format, ##__VA_ARGS__)

#ifdef __cplusplus
}
#endif

#endif // ARES_LOGGING_H
