#include "ares_sequence.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "ares_logging.h"

static uint64_t s_tx_seq = 0;
static uint64_t s_last_rx_seq = 0;
static SemaphoreHandle_t s_seq_mutex = NULL;

void ares_sequence_init(void)
{
    if (s_seq_mutex == NULL) {
        s_seq_mutex = xSemaphoreCreateMutex();
    }
    s_tx_seq = 0;
    s_last_rx_seq = 0;
    ARES_LOGI("Sequence tracking initialized (Replay Defense active)");
}

uint64_t ares_sequence_next_tx(void)
{
    uint64_t val = 0;
    if (s_seq_mutex != NULL) {
        xSemaphoreTake(s_seq_mutex, portMAX_DELAY);
        val = ++s_tx_seq;
        xSemaphoreGive(s_seq_mutex);
    } else {
        val = ++s_tx_seq;
    }
    return val;
}

bool ares_sequence_validate_rx(uint64_t seq)
{
    bool valid = false;
    if (s_seq_mutex != NULL) {
        xSemaphoreTake(s_seq_mutex, portMAX_DELAY);
        if (seq > s_last_rx_seq) {
            s_last_rx_seq = seq;
            valid = true;
        } else {
            ARES_LOGW("Replay defense triggered: sequence %llu <= last %llu",
                      (unsigned long long)seq, (unsigned long long)s_last_rx_seq);
            valid = false;
        }
        xSemaphoreGive(s_seq_mutex);
    } else {
        if (seq > s_last_rx_seq) {
            s_last_rx_seq = seq;
            valid = true;
        }
    }
    return valid;
}

uint64_t ares_sequence_get_last_rx(void)
{
    uint64_t val = 0;
    if (s_seq_mutex != NULL) {
        xSemaphoreTake(s_seq_mutex, portMAX_DELAY);
        val = s_last_rx_seq;
        xSemaphoreGive(s_seq_mutex);
    } else {
        val = s_last_rx_seq;
    }
    return val;
}

void ares_sequence_reset(void)
{
    if (s_seq_mutex != NULL) {
        xSemaphoreTake(s_seq_mutex, portMAX_DELAY);
        s_tx_seq = 0;
        s_last_rx_seq = 0;
        xSemaphoreGive(s_seq_mutex);
    } else {
        s_tx_seq = 0;
        s_last_rx_seq = 0;
    }
    ARES_LOGI("Sequence counter reset");
}
