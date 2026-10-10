package org.ares.agent.transport

import org.ares.agent.protocol.AresEnvelope

/**
 * ARES Transport Interface.
 *
 * Implements Section 1 & 12:
 * Abstract communication channel allowing interchangeable network / mock / test transports.
 */
interface AresTransport {
    fun connect(): Boolean
    fun disconnect()
    fun isConnected(): Boolean
    fun sendMessage(envelope: AresEnvelope): AresEnvelope?
}
