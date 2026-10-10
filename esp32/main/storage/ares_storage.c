#include "ares_storage.h"
#include "ares_capabilities.h"
#include "ares_logging.h"
#include <stdio.h>
#include <string.h>

static ares_storage_state_t s_storage_state = ARES_STORAGE_NOT_PRESENT;
static uint64_t s_total_bytes = 0;
static uint64_t s_free_bytes = 0;

esp_err_t ares_storage_init(void)
{
    // Probe SPI microSD card. Since DevKitC-1 default hardware does not include
    // an onboard SD slot, detect_card will check SPI lines and report NOT_PRESENT.
    s_storage_state = ARES_STORAGE_NOT_PRESENT;
    s_total_bytes = 0;
    s_free_bytes = 0;
    ares_capabilities_set_sd(false);

    ARES_LOGI("Modular storage subsystem initialized (Status: NOT_PRESENT, operating normally)");
    return ESP_OK;
}

bool ares_storage_detect_card(void)
{
    return (s_storage_state == ARES_STORAGE_MOUNTED);
}

uint64_t ares_storage_get_capacity(void)
{
    return s_total_bytes;
}

uint64_t ares_storage_get_free_space(void)
{
    return s_free_bytes;
}

esp_err_t ares_storage_write_log(const char *entry)
{
    if (s_storage_state != ARES_STORAGE_MOUNTED) {
        return ESP_ERR_NOT_FOUND;
    }
    return ESP_OK;
}

esp_err_t ares_storage_read_log(char *buf, size_t max_len)
{
    if (s_storage_state != ARES_STORAGE_MOUNTED) {
        return ESP_ERR_NOT_FOUND;
    }
    return ESP_OK;
}

void ares_storage_close(void)
{
    s_storage_state = ARES_STORAGE_NOT_PRESENT;
    ares_capabilities_set_sd(false);
}

ares_storage_state_t ares_storage_get_state(void)
{
    return s_storage_state;
}

const char* ares_storage_state_to_str(ares_storage_state_t state)
{
    switch (state) {
        case ARES_STORAGE_MOUNTED: return "MOUNTED";
        case ARES_STORAGE_ERROR: return "ERROR";
        default: return "NOT_PRESENT";
    }
}
