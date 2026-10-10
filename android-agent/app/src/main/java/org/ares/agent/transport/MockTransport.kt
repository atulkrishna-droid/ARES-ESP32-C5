package org.ares.agent.transport

import org.ares.agent.protocol.AresEnvelope
import org.ares.agent.protocol.AresMessageTypes
import java.util.UUID

/**
 * In-Memory Mock Transport for Unit and Integration Testing.
 *
 * Implements Section 13:
 * Allows deterministic validation of state machine, enrollment, sequence numbers, and assessment dispatch.
 */
class MockTransport(
    private val expectedDeviceId: String = "ares-android-test01"
) : AresTransport {

    var simulateNetworkFailure: Boolean = false
    var simulateRevocation: Boolean = false
    val transmittedMessages = mutableListOf<AresEnvelope>()
    private var isConnectedState = true
    private var sequenceCounter = 1L

    override fun connect(): Boolean {
        if (simulateNetworkFailure) {
            isConnectedState = false
            return false
        }
        isConnectedState = true
        return true
    }

    override fun disconnect() {
        isConnectedState = false
    }

    override fun isConnected(): Boolean = isConnectedState

    override fun sendMessage(envelope: AresEnvelope): AresEnvelope? {
        if (!isConnectedState || simulateNetworkFailure) {
            return null
        }
        transmittedMessages.add(envelope)

        if (simulateRevocation) {
            return AresEnvelope(
                protocol = "ARES/1.0",
                messageId = UUID.randomUUID().toString(),
                deviceId = envelope.deviceId,
                timestamp = envelope.timestamp,
                type = AresMessageTypes.ERROR,
                sequence = sequenceCounter++,
                payload = mapOf(
                    "code" to "DEVICE_REVOKED",
                    "message" to "Device authorization has been revoked."
                ),
                signature = "MOCK_SIG"
            )
        }

        return when (envelope.type) {
            AresMessageTypes.HELLO -> AresEnvelope(
                protocol = "ARES/1.0",
                messageId = UUID.randomUUID().toString(),
                deviceId = envelope.deviceId,
                timestamp = envelope.timestamp,
                type = AresMessageTypes.HELLO,
                sequence = sequenceCounter++,
                payload = mapOf(
                    "status" to "AUTHORIZED",
                    "authorized_case_id" to "case-test-uuid-001"
                ),
                signature = "MOCK_SIG"
            )
            AresMessageTypes.DEVICE_INFO -> AresEnvelope(
                protocol = "ARES/1.0",
                messageId = UUID.randomUUID().toString(),
                deviceId = envelope.deviceId,
                timestamp = envelope.timestamp,
                type = AresMessageTypes.DEVICE_INFO,
                sequence = sequenceCounter++,
                payload = mapOf("status" to "ACK"),
                signature = "MOCK_SIG"
            )
            AresMessageTypes.CAPABILITIES -> AresEnvelope(
                protocol = "ARES/1.0",
                messageId = UUID.randomUUID().toString(),
                deviceId = envelope.deviceId,
                timestamp = envelope.timestamp,
                type = AresMessageTypes.CAPABILITIES,
                sequence = sequenceCounter++,
                payload = mapOf("status" to "ACK"),
                signature = "MOCK_SIG"
            )
            AresMessageTypes.HEARTBEAT -> AresEnvelope(
                protocol = "ARES/1.0",
                messageId = UUID.randomUUID().toString(),
                deviceId = envelope.deviceId,
                timestamp = envelope.timestamp,
                type = AresMessageTypes.HEARTBEAT,
                sequence = sequenceCounter++,
                payload = mapOf("status" to "ALIVE"),
                signature = "MOCK_SIG"
            )
            AresMessageTypes.EVIDENCE_METADATA -> AresEnvelope(
                protocol = "ARES/1.0",
                messageId = UUID.randomUUID().toString(),
                deviceId = envelope.deviceId,
                timestamp = envelope.timestamp,
                type = AresMessageTypes.EVIDENCE_METADATA,
                sequence = sequenceCounter++,
                payload = mapOf(
                    "status" to "INGESTED",
                    "evidence_id" to (envelope.payload["evidence_id"] ?: "mock-evidence-id")
                ),
                signature = "MOCK_SIG"
            )
            else -> AresEnvelope(
                protocol = "ARES/1.0",
                messageId = UUID.randomUUID().toString(),
                deviceId = envelope.deviceId,
                timestamp = envelope.timestamp,
                type = AresMessageTypes.GET_STATUS,
                sequence = sequenceCounter++,
                payload = mapOf("status" to "READY"),
                signature = "MOCK_SIG"
            )
        }
    }
}
