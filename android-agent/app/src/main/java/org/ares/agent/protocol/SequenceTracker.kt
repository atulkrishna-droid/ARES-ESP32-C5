package org.ares.agent.protocol

import java.util.concurrent.atomic.AtomicLong

/**
 * Replay Defense and Monotonic Sequence Tracker.
 *
 * Implements Section 6 & 13:
 * Enforces sequence > last_received_sequence to defeat frame replaying attacks.
 */
class SequenceTracker(initialOutbound: Long = 0) {
    private val outboundSeq = AtomicLong(initialOutbound)
    private var lastInboundSeq = 0L

    @Synchronized
    fun nextOutboundSequence(): Long {
        return outboundSeq.incrementAndGet()
    }

    @Synchronized
    fun currentOutboundSequence(): Long {
        return outboundSeq.get()
    }

    /**
     * Validates and advances inbound sequence counter.
     * Rejects sequence <= lastInboundSeq.
     */
    @Synchronized
    fun validateAndRecordInbound(sequence: Long): Boolean {
        if (sequence <= lastInboundSeq) {
            return false
        }
        lastInboundSeq = sequence
        return true
    }

    @Synchronized
    fun getLastInboundSequence(): Long = lastInboundSeq

    @Synchronized
    fun reset(outbound: Long = 0, inbound: Long = 0) {
        outboundSeq.set(outbound)
        lastInboundSeq = inbound
    }
}
