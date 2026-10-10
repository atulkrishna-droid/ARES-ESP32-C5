#include "ares_clock.h"
#include "ares_logging.h"
#include <sys/time.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static bool s_synchronized = false;

void ares_clock_init(void)
{
    // If not synchronized, default to base build epoch
    s_synchronized = false;
    ARES_LOGI("Clock subsystem initialized (Awaiting authoritative sync)");
}

void ares_clock_get_iso8601(char *buf, size_t buf_len)
{
    if (buf == NULL || buf_len < 25) return;

    struct timeval tv;
    gettimeofday(&tv, NULL);
    struct tm tm_info;
    gmtime_r(&tv.tv_sec, &tm_info);

    // Format: 2026-09-27T18:45:00Z
    snprintf(buf, buf_len, "%04d-%02d-%02dT%02d:%02d:%02dZ",
             tm_info.tm_year + 1900, tm_info.tm_mon + 1, tm_info.tm_mday,
             tm_info.tm_hour, tm_info.tm_min, tm_info.tm_sec);
}

bool ares_clock_parse_iso8601(const char *iso_str, time_t *out_time)
{
    if (iso_str == NULL || out_time == NULL) return false;

    struct tm tm_val;
    memset(&tm_val, 0, sizeof(tm_val));

    // Support YYYY-MM-DDTHH:MM:SS or YYYY-MM-DDTHH:MM:SSZ
    int yr, mo, dy, hr, mn, sc;
    if (sscanf(iso_str, "%d-%d-%dT%d:%d:%d", &yr, &mo, &dy, &hr, &mn, &sc) >= 6) {
        tm_val.tm_year = yr - 1900;
        tm_val.tm_mon = mo - 1;
        tm_val.tm_mday = dy;
        tm_val.tm_hour = hr;
        tm_val.tm_min = mn;
        tm_val.tm_sec = sc;
        *out_time = mktime(&tm_val);
        return true;
    }
    return false;
}

bool ares_clock_validate_skew(const char *iso_str)
{
    if (!s_synchronized) {
        // If not yet synchronized, accept initial incoming timestamp and sync
        time_t t_remote;
        if (ares_clock_parse_iso8601(iso_str, &t_remote)) {
            ares_clock_sync(t_remote);
            return true;
        }
        return false;
    }

    time_t t_remote;
    if (!ares_clock_parse_iso8601(iso_str, &t_remote)) {
        return false;
    }

    struct timeval tv;
    gettimeofday(&tv, NULL);
    long diff = (long)(t_remote - tv.tv_sec);
    if (diff < 0) diff = -diff;

    if (diff > ARES_MAX_CLOCK_SKEW_SEC) {
        ARES_LOGW("Clock skew rejected: diff %ld seconds exceeds window %d",
                  diff, ARES_MAX_CLOCK_SKEW_SEC);
        return false;
    }
    return true;
}

void ares_clock_sync(time_t epoch_sec)
{
    struct timeval tv = { .tv_sec = epoch_sec, .tv_usec = 0 };
    settimeofday(&tv, NULL);
    s_synchronized = true;
    char iso_buf[32];
    ares_clock_get_iso8601(iso_buf, sizeof(iso_buf));
    ARES_LOGI("System clock synchronized to: %s", iso_buf);
}

bool ares_clock_is_synchronized(void)
{
    return s_synchronized;
}
