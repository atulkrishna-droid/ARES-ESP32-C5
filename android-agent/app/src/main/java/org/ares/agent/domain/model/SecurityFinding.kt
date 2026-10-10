package org.ares.agent.domain.model

import kotlinx.serialization.Serializable

enum class FindingSeverity {
    INFO,
    LOW,
    MEDIUM,
    HIGH,
    CRITICAL
}

/**
 * Deterministic Security Assessment Finding.
 *
 * Implements Section 5 requirements:
 * Provides concrete rule definitions and structured evidence references.
 */
@Serializable
data class SecurityFinding(
    val findingId: String,          // e.g. "finding-f89b3c4a"
    val ruleId: String,             // e.g. "ANDROID-SEC-001"
    val severity: FindingSeverity,
    val title: String,
    val description: String,
    val evidenceReference: String,  // SHA-256 or URI reference to evidence artifact
    val timestamp: String,          // ISO 8601 UTC
    val ruleVersion: String = "1.0.0",
    val recommendation: String,
    val details: Map<String, String> = emptyMap()
)
