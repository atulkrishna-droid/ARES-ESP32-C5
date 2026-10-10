package org.ares.agent.protocol

/**
 * Standard ARES/1.0 Message Types supported by Android Agent.
 *
 * Implements Section 6 & 10.
 */
object AresMessageTypes {
    const val HELLO = "HELLO"
    const val DEVICE_INFO = "DEVICE_INFO"
    const val CAPABILITIES = "CAPABILITIES"
    const val HEARTBEAT = "HEARTBEAT"
    const val GET_STATUS = "GET_STATUS"
    const val GET_TELEMETRY = "GET_TELEMETRY"
    const val ASSESSMENT_START = "ASSESSMENT_START"
    const val ASSESSMENT_STOP = "ASSESSMENT_STOP"
    const val ASSESSMENT_RESULT = "ASSESSMENT_RESULT"
    const val EVIDENCE_METADATA = "EVIDENCE_METADATA"
    const val ERROR = "ERROR"

    val ALLOWED_TYPES = setOf(
        HELLO,
        DEVICE_INFO,
        CAPABILITIES,
        HEARTBEAT,
        GET_STATUS,
        GET_TELEMETRY,
        ASSESSMENT_START,
        ASSESSMENT_STOP,
        ASSESSMENT_RESULT,
        EVIDENCE_METADATA,
        ERROR
    )
}
