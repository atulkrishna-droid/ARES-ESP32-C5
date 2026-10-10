#include "ares_logging.h"

void ares_logging_init(void)
{
    esp_log_level_set(ARES_TAG, ESP_LOG_INFO);
    ESP_LOGI(ARES_TAG, "Logging subsystem initialized (redaction active, no secrets logged)");
}
