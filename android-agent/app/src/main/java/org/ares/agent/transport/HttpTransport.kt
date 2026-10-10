package org.ares.agent.transport

import org.ares.agent.protocol.AresEnvelope
import org.ares.agent.security.RedactingLogger
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

/**
 * HTTPS REST / Protocol Transport connecting to ARES FastAPI backend.
 *
 * Implements Section 1, 6 & 12:
 * Dispatches ARES/1.0 envelopes to backend endpoints and returns parsed responses.
 */
class HttpTransport(
    private val baseUrl: String = "http://10.0.2.2:8000/api/v1/android",
    private val connectTimeoutMs: Int = 5000,
    private val readTimeoutMs: Int = 10000
) : AresTransport {

    @Volatile
    private var connected: Boolean = false

    override fun connect(): Boolean {
        // Ping health endpoint to confirm reachability
        return try {
            val url = URL("$baseUrl/health")
            val conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "GET"
            conn.connectTimeout = connectTimeoutMs
            conn.readTimeout = readTimeoutMs
            val responseCode = conn.responseCode
            conn.disconnect()
            connected = (responseCode in 200..299)
            connected
        } catch (e: Exception) {
            RedactingLogger.w("HttpTransport", "Connect probe failed: ${e.message}")
            connected = false
            false
        }
    }

    override fun disconnect() {
        connected = false
        RedactingLogger.i("HttpTransport", "Transport disconnected.")
    }

    override fun isConnected(): Boolean = connected

    override fun sendMessage(envelope: AresEnvelope): AresEnvelope? {
        val endpoint = when (envelope.type) {
            "HELLO", "DEVICE_INFO", "CAPABILITIES" -> "$baseUrl/handshake"
            "HEARTBEAT", "GET_TELEMETRY" -> "$baseUrl/telemetry"
            "EVIDENCE_METADATA" -> "$baseUrl/evidence"
            else -> "$baseUrl/message"
        }

        return try {
            val url = URL(endpoint)
            val conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.setRequestProperty("Content-Type", "application/json")
            conn.setRequestProperty("Accept", "application/json")
            conn.connectTimeout = connectTimeoutMs
            conn.readTimeout = readTimeoutMs
            conn.doOutput = true

            val jsonBody = envelope.toJsonString()
            OutputStreamWriter(conn.outputStream).use { writer ->
                writer.write(jsonBody)
                writer.flush()
            }

            val responseCode = conn.responseCode
            if (responseCode in 200..299) {
                val responseText = BufferedReader(InputStreamReader(conn.inputStream)).use { it.readText() }
                conn.disconnect()
                connected = true
                AresEnvelope.fromJsonString(responseText)
            } else {
                val errText = BufferedReader(InputStreamReader(conn.errorStream ?: conn.inputStream)).use { it.readText() }
                conn.disconnect()
                RedactingLogger.e("HttpTransport", "Server returned HTTP $responseCode: $errText")
                null
            }
        } catch (e: Exception) {
            RedactingLogger.e("HttpTransport", "Network transmission error: ${e.message}")
            connected = false
            null
        }
    }
}
