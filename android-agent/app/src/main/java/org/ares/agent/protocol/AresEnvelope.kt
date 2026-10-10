package org.ares.agent.protocol

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonObject
import org.json.JSONObject

/**
 * Standard ARES/1.0 Message Envelope.
 *
 * Implements Section 6:
 * Conforms identically to the backend's AresProtocol specification.
 */
data class AresEnvelope(
    val protocol: String = "ARES/1.0",
    val messageId: String,
    val deviceId: String,
    val timestamp: String,
    val type: String,
    val sequence: Long,
    val payload: Map<String, Any?> = emptyMap(),
    val signature: String = "UNSIGNED"
) {
    /**
     * Produces deterministic canonical JSON representation of envelope without signature field.
     */
    fun canonicalBytes(): ByteArray {
        val json = JSONObject()
        json.put("protocol", protocol)
        json.put("message_id", messageId)
        json.put("device_id", deviceId)
        json.put("timestamp", timestamp)
        json.put("type", type)
        json.put("sequence", sequence)

        // Nested payload
        val payloadJson = JSONObject(payload)
        json.put("payload", payloadJson)

        return json.toString().toByteArray(Charsets.UTF_8)
    }

    /**
     * Converts to JSON string for transmission.
     */
    fun toJsonString(): String {
        val json = JSONObject()
        json.put("protocol", protocol)
        json.put("message_id", messageId)
        json.put("device_id", deviceId)
        json.put("timestamp", timestamp)
        json.put("type", type)
        json.put("sequence", sequence)
        json.put("payload", JSONObject(payload))
        json.put("signature", signature)
        return json.toString()
    }

    companion object {
        fun fromJsonString(jsonString: String): AresEnvelope {
            val obj = JSONObject(jsonString)
            val payloadMap = mutableMapOf<String, Any?>()
            if (obj.has("payload")) {
                val pObj = obj.getJSONObject("payload")
                for (key in pObj.keys()) {
                    payloadMap[key] = pObj.get(key)
                }
            }

            return AresEnvelope(
                protocol = obj.optString("protocol", "ARES/1.0"),
                messageId = obj.getString("message_id"),
                deviceId = obj.getString("device_id"),
                timestamp = obj.getString("timestamp"),
                type = obj.getString("type"),
                sequence = obj.getLong("sequence"),
                payload = payloadMap,
                signature = obj.optString("signature", "UNSIGNED")
            )
        }
    }
}
