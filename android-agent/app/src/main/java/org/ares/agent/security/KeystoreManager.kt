package org.ares.agent.security

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import java.security.MessageDigest
import javax.crypto.KeyGenerator
import javax.crypto.Mac
import javax.crypto.SecretKey

/**
 * Android Keystore & Cryptographic Signature Provider.
 *
 * Implements Section 2 & 6:
 * - Generates and stores HMAC-SHA256 keys inside AndroidKeyStore provider where supported.
 * - Signs ARES/1.0 protocol frames.
 * - Performs constant-time signature verification.
 * - Private keys are never exposed in plaintext.
 */
class KeystoreManager(
    private val keyAlias: String = "ares_device_signing_key",
    private val isAndroidKeystoreAvailable: Boolean = try {
        KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        true
    } catch (_: Throwable) {
        false
    }
) {
    private var softwareFallbackKey: SecretKey? = null

    init {
        ensureKeyExists()
    }

    private fun ensureKeyExists() {
        if (isAndroidKeystoreAvailable) {
            try {
                val keyStore = KeyStore.getInstance("AndroidKeyStore")
                keyStore.load(null)
                if (!keyStore.containsAlias(keyAlias)) {
                    val keyGen = KeyGenerator.getInstance("HmacSHA256", "AndroidKeyStore")
                    keyGen.init(
                        KeyGenParameterSpec.Builder(
                            keyAlias,
                            KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY
                        ).setKeySize(256).build()
                    )
                    keyGen.generateKey()
                }
            } catch (e: Exception) {
                RedactingLogger.e("KeystoreManager", "AndroidKeyStore key initialization failed: ${e.message}")
                throw IllegalStateException("Secure Android signing key is unavailable.", e)
            }
        } else {
            // JVM-only fallback for local unit tests. Real Android runtime fails closed above.
            generateSoftwareKey()
        }
    }

    private fun generateSoftwareKey() {
        if (softwareFallbackKey == null) {
            val keyGen = KeyGenerator.getInstance("HmacSHA256")
            keyGen.init(256)
            softwareFallbackKey = keyGen.generateKey()
        }
    }

    /**
     * Compute HMAC-SHA256 over message bytes.
     */
    fun sign(data: ByteArray): String {
        val mac = Mac.getInstance("HmacSHA256")
        val key = getSecretKey()
        mac.init(key)
        val signatureBytes = mac.doFinal(data)
        return signatureBytes.joinToString("") { "%02x".format(it) }
    }

    /**
     * Constant-time signature verification.
     */
    fun verify(data: ByteArray, receivedSignatureHex: String): Boolean {
        val computedHex = sign(data)
        return MessageDigest.isEqual(
            computedHex.toByteArray(Charsets.UTF_8),
            receivedSignatureHex.toByteArray(Charsets.UTF_8)
        )
    }

    private fun getSecretKey(): SecretKey {
        if (isAndroidKeystoreAvailable) {
            val keyStore = KeyStore.getInstance("AndroidKeyStore")
            keyStore.load(null)
            return keyStore.getKey(keyAlias, null) as? SecretKey
                ?: throw IllegalStateException("Secure Android signing key is unavailable.")
        }
        return softwareFallbackKey ?: run {
            generateSoftwareKey()
            softwareFallbackKey!!
        }
    }
}
