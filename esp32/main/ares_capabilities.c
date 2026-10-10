#include "ares_capabilities.h"
#include "ares_logging.h"
#include <string.h>

static ares_capabilities_t s_caps;
static bool s_initialized = false;

void ares_capabilities_init(void)
{
    if (s_initialized) return;

    memset(&s_caps, 0, sizeof(s_caps));

    // ESP32-C5 Silicon Features
    s_caps.wifi_24 = true;
    s_caps.wifi_5 = true;
    s_caps.wifi6 = true;
    s_caps.ble = true;
    s_caps.bluetooth_classic = false; // Strictly false on ESP32-C5 architecture
    s_caps.ieee802154 = true;
    s_caps.zigbee = true;
    s_caps.thread = true;
    s_caps.usb = true;

    // Optional modules: default to false unless dynamic probe succeeds
    s_caps.sd = false;
    s_caps.gps = false;
    s_caps.battery = false;
    s_caps.display = false;

    s_initialized = true;
    ARES_LOGI("Capabilities initialized: 2.4/5GHz Wi-Fi 6, BLE, IEEE 802.15.4 (BT Classic: FALSE)");
}

void ares_capabilities_get(ares_capabilities_t *out_caps)
{
    if (out_caps == NULL) return;
    if (!s_initialized) {
        ares_capabilities_init();
    }
    memcpy(out_caps, &s_caps, sizeof(ares_capabilities_t));
}

void ares_capabilities_set_sd(bool present)
{
    if (!s_initialized) {
        ares_capabilities_init();
    }
    s_caps.sd = present;
    ARES_LOGI("Modular capability SD updated: %s", present ? "PRESENT" : "ABSENT");
}

void ares_capabilities_populate_json(cJSON *json)
{
    if (json == NULL) return;
    if (!s_initialized) {
        ares_capabilities_init();
    }

    cJSON_AddBoolToObject(json, "wifi_24", s_caps.wifi_24);
    cJSON_AddBoolToObject(json, "wifi_5", s_caps.wifi_5);
    cJSON_AddBoolToObject(json, "wifi6", s_caps.wifi6);
    cJSON_AddBoolToObject(json, "ble", s_caps.ble);
    cJSON_AddBoolToObject(json, "bluetooth_classic", s_caps.bluetooth_classic);
    cJSON_AddBoolToObject(json, "ieee802154", s_caps.ieee802154);
    cJSON_AddBoolToObject(json, "zigbee", s_caps.zigbee);
    cJSON_AddBoolToObject(json, "thread", s_caps.thread);
    cJSON_AddBoolToObject(json, "usb", s_caps.usb);

    // Modular hardware flags
    cJSON_AddBoolToObject(json, "sd", s_caps.sd);
    cJSON_AddBoolToObject(json, "gps", s_caps.gps);
    cJSON_AddBoolToObject(json, "battery", s_caps.battery);
    cJSON_AddBoolToObject(json, "display", s_caps.display);
}
