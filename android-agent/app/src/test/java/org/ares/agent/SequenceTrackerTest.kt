package org.ares.agent

import org.ares.agent.protocol.SequenceTracker
import org.junit.Assert.*
import org.junit.Test

class SequenceTrackerTest {

    @Test
    fun testMonotonicOutboundSequences() {
        val tracker = SequenceTracker()
        assertEquals(1L, tracker.nextOutboundSequence())
        assertEquals(2L, tracker.nextOutboundSequence())
        assertEquals(3L, tracker.nextOutboundSequence())
        assertEquals(3L, tracker.currentOutboundSequence())
    }

    @Test
    fun testInboundReplayDefense() {
        val tracker = SequenceTracker()

        // Initial valid sequence
        assertTrue("Sequence 1 accepted", tracker.validateAndRecordInbound(1L))
        assertEquals(1L, tracker.getLastInboundSequence())

        // Replayed sequence 1 must be rejected
        assertFalse("Replayed sequence 1 rejected", tracker.validateAndRecordInbound(1L))

        // Out-of-order sequence (lower than current) must be rejected
        assertFalse("Stale sequence 0 rejected", tracker.validateAndRecordInbound(0L))

        // Advancing sequence accepted
        assertTrue("Sequence 5 accepted", tracker.validateAndRecordInbound(5L))
        assertEquals(5L, tracker.getLastInboundSequence())

        // Past sequence rejected
        assertFalse("Sequence 4 rejected after 5", tracker.validateAndRecordInbound(4L))
    }
}
