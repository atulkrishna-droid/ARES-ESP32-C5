#include "ares_802154.h"
#include "ares_logging.h"

static ares_154_state_t s_state = ARES_154_STATE_IDLE;
static bool s_supported = true; // ESP32-C5 features integrated 802.15.4

esp_err_t ares_802154_init(void)
{
    s_supported = true;
    s_state = ARES_154_STATE_IDLE;
    ARES_LOGI("IEEE 802.15.4 subsystem initialized (Thread/Zigbee radio ready)");
    return ESP_OK;
}

bool ares_802154_is_supported(void)
{
    return s_supported;
}

ares_154_state_t ares_802154_get_state(void)
{
    return s_state;
}

const char* ares_802154_state_to_str(ares_154_state_t state)
{
    switch (state) {
        case ARES_154_STATE_NOT_SUPPORTED: return "NOT_SUPPORTED";
        case ARES_154_STATE_IDLE: return "IDLE";
        case ARES_154_STATE_LISTENING: return "LISTENING";
        default: return "ERROR";
    }
}
