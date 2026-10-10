package org.ares.agent.domain.model

/**
 * ARES Android Agent Finite State Model.
 *
 * Enforces Section 9 & 10 constraints:
 * - Assessment commands can only execute in [AUTHORIZED] or [BUSY] state.
 * - If connectivity drops, state transitions to [OFFLINE] and active assessments become INTERRUPTED.
 * - Revocation locks down the agent into [REVOKED].
 */
enum class AgentState {
    OFFLINE,
    AUTHENTICATING,
    AUTHORIZED,
    BUSY,
    ERROR,
    REVOKED;

    val canExecuteAssessment: Boolean
        get() = this == AUTHORIZED || this == BUSY
}
