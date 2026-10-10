package org.ares.agent

import org.ares.agent.protocol.AresEnvelope
import org.ares.agent.protocol.AresMessageTypes
import org.ares.agent.protocol.ProtocolValidator
import org.ares.agent.protocol.SequenceTracker
import org.ares.agent.protocol.ValidationResult
import org.ares.agent.security.KeystoreManager
import org.junit.Assert.*
import org.junit.Test
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import java.util.UUID

class ProtocolEnvelopeTest {

    private fun getCurrentIsoTimestamp(): String {
        val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        format.timeZone = TimeZone.getTimeZone("UTC")
        return format.format(Date())
    }

    @Test
    fun testSerializationAndDeserialization() {
        val original = AresEnvelope(
            protocol = "ARES/1.0",
            messageId = UUID.randomUUID().toString(),
            deviceId = "ares-android-11223344",
            timestamp = getCurrentIsoTimestamp(),
            type = AresMessageTypes.HELLO,
            sequence = 1,
            payload = mapOf("status" to "READY", "version" to "1.0.0"),
            signature = "TEST_SIG_HEX"
        )

        val jsonString = original.toJsonString()
        val parsed = AresEnvelope.fromJsonString(jsonString)

        assertEquals(original.protocol, parsed.protocol)
        assertEquals(original.messageId, parsed.messageId)
        assertEquals(original.deviceId, parsed.deviceId)
        assertEquals(original.type, parsed.type)
        assertEquals(original.sequence, parsed.sequence)
        assertEquals("READY", parsed.payload["status"])
    }

    @Test
    fun testSignatureVerification() {
        val keystore = KeystoreManager()
        val env = AresEnvelope(
            messageId = UUID.randomUUID().toString(),
            deviceId = "ares-android-11223344",
            timestamp = getCurrentIsoTimestamp(),
            type = AresMessageTypes.DEVICE_INFO,
            sequence = 2,
            payload = mapOf("model" to "Pixel")
        )

        val sig = keystore.sign(env.canonicalBytes())
        val signedEnv = env.copy(signature = sig)

        val validator = ProtocolValidator("ares-android-11223344", keystore)
        val res = validator.validate(signedEnv, verifySignature = true)
        assertTrue(res is ValidationResult.Valid)

        // Corrupted signature rejection
        val badEnv = signedEnv.copy(signature = sig.reversed())
        val badRes = validator.validate(badEnv, verifySignature = true)
        assertTrue(badRes is ValidationResult.Invalid)
        assertEquals("INVALID_SIGNATURE", (badRes as ValidationResult.Invalid).code)
    }

    @Test
    fun testClockSkewRejection() {
        val validator = ProtocolValidator("ares-android-11223344", maxClockSkewSeconds = 60)
        // Timestamp 10 minutes in the past
        val oldTimestamp = "2020-01-01T00:00:00Z"
        val oldEnv = AresEnvelope(
            messageId = UUID.randomUUID().toString(),
            deviceId = "ares-android-11223344",
            timestamp = oldTimestamp,
            type = AresMessageTypes.HEARTBEAT,
            sequence = 1
        )
        val res = validator.validate(oldEnv, verifySignature = false)
        assertTrue(res is ValidationResult.Invalid)
        assertEquals("TIMESTAMP_EXPIRED", (res as ValidationResult.Invalid).code)
    }
}
