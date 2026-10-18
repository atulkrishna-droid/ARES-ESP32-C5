package org.ares.agent.protocol

import org.ares.agent.security.KeystoreManager
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

sealed class ValidationResult {
    object Valid : ValidationResult()
    data class Invalid(val code: String, val reason: String) : ValidationResult()
}

/**
 * Inbound Protocol Envelope Validator.
 *
 * Implements Section 6 & 11:
 * Validates protocol version, message types, timestamps, sequences, and HMAC signatures.
 */
class ProtocolValidator(
    private val expectedDeviceId: String,
    private val keystoreManager: KeystoreManager? = null,
    private val sequenceTracker: SequenceTracker = SequenceTracker(),
    private val maxClockSkewSeconds: Long = 60L
) {
    companion object {
        const val PROTOCOL_ARES_1 = "ARES/1.0"
        const val PROTOCOL_ARES_MOBILE_1 = "ARES-MOBILE/1.0"
    }

    fun validate(envelope: AresEnvelope, verifySignature: Boolean = true): ValidationResult {
        // 1. Protocol Version
        if (envelope.protocol != PROTOCOL_ARES_1 && envelope.protocol != PROTOCOL_ARES_MOBILE_1) {
            return ValidationResult.Invalid("INVALID_PROTOCOL", "Unsupported protocol version: ${envelope.protocol}")
        }

        // 2. Message Type
        if (envelope.type !in AresMessageTypes.ALLOWED_TYPES) {
            return ValidationResult.Invalid("INVALID_MESSAGE_TYPE", "Message type '${envelope.type}' is not whitelisted.")
        }

        // 3. Device ID matching
        if (envelope.deviceId != expectedDeviceId && envelope.deviceId != "BROADCAST") {
            return ValidationResult.Invalid("INVALID_DEVICE", "Target device mismatch: got '${envelope.deviceId}', expected '$expectedDeviceId'")
        }

        // 4. Timestamp clock skew
        val skewValidation = validateTimestamp(envelope.timestamp)
        if (skewValidation is ValidationResult.Invalid) {
            return skewValidation
        }

        // Verify authenticity before touching replay state. Otherwise an unauthenticated
        // message can consume a valid sequence number and deny service to the real peer.
        if (verifySignature) {
            if (keystoreManager == null || envelope.signature.isBlank() || envelope.signature == "UNSIGNED") {
                return ValidationResult.Invalid("INVALID_SIGNATURE", "A signed message and verifier are required.")
            }
            if (!keystoreManager.verify(envelope.canonicalBytes(), envelope.signature)) {
                return ValidationResult.Invalid("INVALID_SIGNATURE", "HMAC-SHA256 signature verification failed.")
            }
        }

        // Replay state changes only after structural, timestamp, and signature checks pass.
        if (!sequenceTracker.validateAndRecordInbound(envelope.sequence)) {
            return ValidationResult.Invalid("INVALID_SEQUENCE", "Replayed or out-of-order sequence number: ${envelope.sequence} <= ${sequenceTracker.getLastInboundSequence()}")
        }

        return ValidationResult.Valid
    }

    private fun validateTimestamp(timestampStr: String): ValidationResult {
        return try {
            val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US)
            format.timeZone = TimeZone.getTimeZone("UTC")
            val cleanStr = timestampStr.replace("Z", "").substringBefore("+").substringBefore(".")
            val msgDate = format.parse(cleanStr) ?: return ValidationResult.Invalid("INVALID_TIMESTAMP", "Unparseable timestamp format.")
            val now = Date()
            val deltaSeconds = Math.abs(now.time - msgDate.time) / 1000L

            if (deltaSeconds > maxClockSkewSeconds) {
                ValidationResult.Invalid("TIMESTAMP_EXPIRED", "Message timestamp clock skew ($deltaSeconds s) exceeds tolerance ($maxClockSkewSeconds s).")
            } else {
                ValidationResult.Valid
            }
        } catch (_: Exception) {
            ValidationResult.Invalid("INVALID_TIMESTAMP", "Failed to parse ISO-8601 timestamp.")
        }
    }
}
