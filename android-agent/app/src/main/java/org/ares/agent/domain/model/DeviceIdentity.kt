package org.ares.agent.domain.model

import kotlinx.serialization.Serializable

/**
 * ARES Device Identity Model.
 *
 * Implements Section 2:
 * - Does NOT access privileged hardware identifiers (IMEI, MEID, Serial).
 * - Generates an ARES-scoped cryptographic identifier: ares-android-xxxxxxxx.
 * - Manages public key representations and enrollment metadata.
 */
@Serializable
data class DeviceIdentity(
    val deviceId: String,          // e.g. "ares-android-a1b2c3d4e5f6"
    val enrollmentId: String,      // UUID established upon backend registration
    val publicKeyHex: String,      // Exportable public key for signature validation
    val keyAlias: String,          // Keystore entry alias
    val algorithm: String = "HMAC-SHA256",
    val enrolledAt: String,        // ISO 8601 UTC timestamp
    val keyVersion: Int = 1
) {
    init {
        require(deviceId.startsWith("ares-android-")) {
            "Device identity must follow standard prefix 'ares-android-'"
        }
    }
}
