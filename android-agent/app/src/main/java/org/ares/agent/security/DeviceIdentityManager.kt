package org.ares.agent.security

import org.ares.agent.domain.model.DeviceIdentity
import java.security.SecureRandom
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import java.util.UUID

/**
 * Device Identity Generator and State Coordinator.
 *
 * Implements Section 2:
 * - Generates unprivileged identifier: ares-android-xxxxxxxx
 * - Coordinates enrollment state and key management
 * - Handles revocation locks
 */
class DeviceIdentityManager(
    private val keystoreManager: KeystoreManager = KeystoreManager(),
    private val memoryStore: MutableMap<String, String> = mutableMapOf()
) {
    companion object {
        private const val KEY_DEVICE_ID = "ares_device_id"
        private const val KEY_ENROLLMENT_ID = "ares_enrollment_id"
        private const val KEY_ENROLLED_AT = "ares_enrolled_at"
        private const val KEY_ACTIVE_CASE_ID = "ares_active_case_id"
        private const val KEY_REVOKED = "ares_device_revoked"
    }

    /**
     * Get or generate the persistent ARES device identity.
     */
    fun getOrCreateIdentity(): DeviceIdentity {
        var deviceId = memoryStore[KEY_DEVICE_ID]
        var enrollmentId = memoryStore[KEY_ENROLLMENT_ID]
        var enrolledAt = memoryStore[KEY_ENROLLED_AT]

        if (deviceId == null) {
            val randomBytes = ByteArray(4)
            SecureRandom().nextBytes(randomBytes)
            val hexSuffix = randomBytes.joinToString("") { "%02x".format(it) }
            deviceId = "ares-android-$hexSuffix"
            enrollmentId = UUID.randomUUID().toString()
            enrolledAt = getCurrentIsoTimestamp()

            memoryStore[KEY_DEVICE_ID] = deviceId
            memoryStore[KEY_ENROLLMENT_ID] = enrollmentId
            memoryStore[KEY_ENROLLED_AT] = enrolledAt
            RedactingLogger.i("DeviceIdentityManager", "Generated fresh identity: $deviceId")
        }

        return DeviceIdentity(
            deviceId = deviceId,
            enrollmentId = enrollmentId ?: UUID.randomUUID().toString(),
            publicKeyHex = keystoreManager.getPublicKeyRepresentation(),
            keyAlias = "ares_device_signing_key",
            enrolledAt = enrolledAt ?: getCurrentIsoTimestamp()
        )
    }

    fun isRevoked(): Boolean {
        return memoryStore[KEY_REVOKED] == "true"
    }

    fun markRevoked(reason: String = "Operator Revocation") {
        memoryStore[KEY_REVOKED] = "true"
        RedactingLogger.w("DeviceIdentityManager", "Device identity marked REVOKED: $reason")
    }

    fun setActiveCaseId(caseId: String?) {
        if (caseId != null) {
            memoryStore[KEY_ACTIVE_CASE_ID] = caseId
        } else {
            memoryStore.remove(KEY_ACTIVE_CASE_ID)
        }
    }

    fun getActiveCaseId(): String? {
        return memoryStore[KEY_ACTIVE_CASE_ID]
    }

    private fun getCurrentIsoTimestamp(): String {
        val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        format.timeZone = TimeZone.getTimeZone("UTC")
        return format.format(Date())
    }
}
