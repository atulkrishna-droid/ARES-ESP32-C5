package org.ares.agent.security

import android.util.Log

/**
 * Structured Logging Utility with Mandatory Secret Redaction.
 *
 * Implements Section 1 & 2:
 * Prevents sensitive tokens, HMAC secrets, authorization keys, and passwords from reaching Logcat.
 */
object RedactingLogger {
    private const val DEFAULT_TAG = "ARES-AGENT"

    private val SENSITIVE_PATTERNS = listOf(
        Regex("(?i)(password|secret|token|bearer|signature|private_key)[\"':=\\s]+([a-zA-Z0-9_\\-\\.\\+/]{6,})"),
        Regex("(?i)(key=\")[^\"]+(\")"),
        Regex("(?i)(hmac[_-]?secret[\"':=\\s]+)[a-zA-Z0-9]+")
    )

    fun i(tag: String = DEFAULT_TAG, message: String) {
        val sanitized = sanitize(message)
        println("INFO [$tag] $sanitized")
        try {
            Log.i(tag, sanitized)
        } catch (_: Throwable) {
            // Unit test environment fallback
        }
    }

    fun d(tag: String = DEFAULT_TAG, message: String) {
        val sanitized = sanitize(message)
        println("DEBUG [$tag] $sanitized")
        try {
            Log.d(tag, sanitized)
        } catch (_: Throwable) {}
    }

    fun w(tag: String = DEFAULT_TAG, message: String, throwable: Throwable? = null) {
        val sanitized = sanitize(message)
        println("WARN [$tag] $sanitized ${throwable?.message ?: ""}")
        try {
            Log.w(tag, sanitized, throwable)
        } catch (_: Throwable) {}
    }

    fun e(tag: String = DEFAULT_TAG, message: String, throwable: Throwable? = null) {
        val sanitized = sanitize(message)
        System.err.println("ERROR [$tag] $sanitized ${throwable?.message ?: ""}")
        try {
            Log.e(tag, sanitized, throwable)
        } catch (_: Throwable) {}
    }

    fun sanitize(input: String): String {
        var result = input
        for (pattern in SENSITIVE_PATTERNS) {
            result = pattern.replace(result) { matchResult ->
                val prefix = matchResult.groups[1]?.value ?: ""
                "$prefix[REDACTED]"
            }
        }
        return result
    }
}
