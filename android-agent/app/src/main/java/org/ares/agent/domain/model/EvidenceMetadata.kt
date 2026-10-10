package org.ares.agent.domain.model

import kotlinx.serialization.Serializable

/**
 * Evidence Metadata Record.
 *
 * Implements Section 8:
 * Generates cryptographic evidence metadata without uploading sensitive user files.
 */
@Serializable
data class EvidenceMetadata(
    val evidenceId: String,          // UUID
    val caseId: String,              // Active authorized case UUID
    val assessmentId: String,        // Assessment execution UUID
    val sourceDeviceId: String,      // ares-android-xxxxxxxx
    val timestamp: String,           // ISO 8601 UTC
    val artifactType: String,        // e.g. "APPLICATION_INVENTORY_METADATA", "SECURITY_POSTURE_REPORT"
    val sha256: String,              // Hex digest of canonical representation
    val sha512: String,              // Hex digest of canonical representation
    val acquisitionMetadata: Map<String, String> = emptyMap()
)
