package org.ares.agent

import org.ares.agent.domain.model.AgentState
import org.ares.agent.protocol.AresEnvelope
import org.ares.agent.protocol.AresMessageTypes
import org.ares.agent.transport.MockTransport
import org.junit.Assert.*
import org.junit.Test
import java.util.UUID

class StateMachineTest {

    @Test
    fun testAssessmentExecutionGuard() {
        assertFalse(AgentState.OFFLINE.canExecuteAssessment)
        assertFalse(AgentState.AUTHENTICATING.canExecuteAssessment)
        assertFalse(AgentState.ERROR.canExecuteAssessment)
        assertFalse(AgentState.REVOKED.canExecuteAssessment)

        assertTrue(AgentState.AUTHORIZED.canExecuteAssessment)
        assertTrue(AgentState.BUSY.canExecuteAssessment)
    }

    @Test
    fun testMockTransportHandshakeFlow() {
        val transport = MockTransport("ares-android-test01")
        assertTrue(transport.connect())

        val hello = AresEnvelope(
            messageId = UUID.randomUUID().toString(),
            deviceId = "ares-android-test01",
            timestamp = "2026-09-27T14:00:00Z",
            type = AresMessageTypes.HELLO,
            sequence = 1
        )

        val resp = transport.sendMessage(hello)
        assertNotNull(resp)
        assertEquals("AUTHORIZED", resp?.payload?.get("status"))
        assertEquals("case-test-uuid-001", resp?.payload?.get("authorized_case_id"))
    }

    @Test
    fun testNetworkFailureYieldsNull() {
        val transport = MockTransport("ares-android-test01")
        transport.simulateNetworkFailure = true
        assertFalse(transport.connect())

        val hello = AresEnvelope(
            messageId = UUID.randomUUID().toString(),
            deviceId = "ares-android-test01",
            timestamp = "2026-09-27T14:00:00Z",
            type = AresMessageTypes.HELLO,
            sequence = 1
        )
        val resp = transport.sendMessage(hello)
        assertNull("Disconnected transport returns null", resp)
    }

    @Test
    fun testRevocationResponseHandling() {
        val transport = MockTransport("ares-android-test01")
        transport.simulateRevocation = true

        val hello = AresEnvelope(
            messageId = UUID.randomUUID().toString(),
            deviceId = "ares-android-test01",
            timestamp = "2026-09-27T14:00:00Z",
            type = AresMessageTypes.HELLO,
            sequence = 1
        )
        val resp = transport.sendMessage(hello)
        assertNotNull(resp)
        assertEquals(AresMessageTypes.ERROR, resp?.type)
        assertEquals("DEVICE_REVOKED", resp?.payload?.get("code"))
    }
}
