package org.ares.agent.security

import android.content.SharedPreferences
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
    private val memoryStore: MutableMap<String, String> = mutableMapOf(),
    private val persistentStore: DeviceIdentityStore? = null
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
        var deviceId = get(KEY_DEVICE_ID)
        var enrollmentId = get(KEY_ENROLLMENT_ID)
        var enrolledAt = get(KEY_ENROLLED_AT)

        if (deviceId != null && !deviceId.startsWith("ares-android-")) {
            // Preserve a legacy identity and stop. Replacing it automatically could
            // create a second backend record and falsely imply that it was enrolled.
            throw LegacyDeviceIdentityException(deviceId)
        }

        if (deviceId == null) {
            val randomBytes = ByteArray(4)
            SecureRandom().nextBytes(randomBytes)
            val hexSuffix = randomBytes.joinToString("") { "%02x".format(it) }
            deviceId = "ares-android-$hexSuffix"
            enrollmentId = UUID.randomUUID().toString()
            enrolledAt = getCurrentIsoTimestamp()

            put(KEY_DEVICE_ID, deviceId)
            put(KEY_ENROLLMENT_ID, enrollmentId)
            put(KEY_ENROLLED_AT, enrolledAt)
            RedactingLogger.i("DeviceIdentityManager", "Generated fresh identity: $deviceId")
        }

        return DeviceIdentity(
            deviceId = deviceId,
            enrollmentId = enrollmentId ?: UUID.randomUUID().toString(),
            keyAlias = "ares_device_signing_key",
            enrolledAt = enrolledAt ?: getCurrentIsoTimestamp()
        )
    }

    fun isRevoked(): Boolean {
        return get(KEY_REVOKED) == "true"
    }

    fun markRevoked(reason: String = "Operator Revocation") {
        put(KEY_REVOKED, "true")
        RedactingLogger.w("DeviceIdentityManager", "Device identity marked REVOKED: $reason")
    }

    fun setActiveCaseId(caseId: String?) {
        if (caseId != null) {
            put(KEY_ACTIVE_CASE_ID, caseId)
        } else {
            remove(KEY_ACTIVE_CASE_ID)
        }
    }

    fun getActiveCaseId(): String? {
        return get(KEY_ACTIVE_CASE_ID)
    }

    private fun get(key: String): String? = persistentStore?.get(key) ?: memoryStore[key]

    private fun put(key: String, value: String) {
        memoryStore[key] = value
        persistentStore?.put(key, value)
    }

    private fun remove(key: String) {
        memoryStore.remove(key)
        persistentStore?.remove(key)
    }

    private fun getCurrentIsoTimestamp(): String {
        val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        format.timeZone = TimeZone.getTimeZone("UTC")
        return format.format(Date())
    }
}

interface DeviceIdentityStore {
    fun get(key: String): String?
    fun put(key: String, value: String)
    fun remove(key: String)
}

class SharedPreferencesIdentityStore(private val preferences: SharedPreferences) : DeviceIdentityStore {
    override fun get(key: String): String? = preferences.getString(key, null)

    override fun put(key: String, value: String) {
        check(preferences.edit().putString(key, value).commit()) {
            "Could not persist the ARES device identity."
        }
    }

    override fun remove(key: String) {
        check(preferences.edit().remove(key).commit()) {
            "Could not update persistent ARES identity state."
        }
    }
}

class LegacyDeviceIdentityException(val legacyDeviceId: String) :
    IllegalStateException("Legacy device identity requires operator migration.")
