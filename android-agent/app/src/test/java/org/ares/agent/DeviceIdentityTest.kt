package org.ares.agent

import org.ares.agent.security.DeviceIdentityManager
import org.ares.agent.security.KeystoreManager
import org.junit.Assert.*
import org.junit.Test

class DeviceIdentityTest {

    @Test
    fun testIdentityFormatAndPersistence() {
        val memoryStore = mutableMapOf<String, String>()
        val keystoreManager = KeystoreManager()
        val manager = DeviceIdentityManager(keystoreManager, memoryStore)

        val id1 = manager.getOrCreateIdentity()
        assertTrue("Device ID must start with ares-android-", id1.deviceId.startsWith("ares-android-"))
        assertEquals(21, id1.deviceId.length) // "ares-android-" (13) + 8 hex chars = 21

        // Reopening the manager against the same backing store models a process restart.
        val id2 = DeviceIdentityManager(keystoreManager, memoryStore).getOrCreateIdentity()
        assertEquals(id1.deviceId, id2.deviceId)
        assertEquals(id1.enrollmentId, id2.enrollmentId)
    }

    @Test
    fun legacyIdentityIsPreservedAndNeverSilentlyReplaced() {
        val store = mutableMapOf("ares_device_id" to "android-bd4d600d")
        val manager = DeviceIdentityManager(KeystoreManager(), store)

        try {
            manager.getOrCreateIdentity()
            fail("Legacy identity must require an explicit migration decision")
        } catch (expected: org.ares.agent.security.LegacyDeviceIdentityException) {
            assertEquals("android-bd4d600d", expected.legacyDeviceId)
        }

        assertEquals("android-bd4d600d", store["ares_device_id"])
        assertEquals(1, store.size)
    }

    @Test
    fun testRevocationLock() {
        val manager = DeviceIdentityManager()
        assertFalse(manager.isRevoked())

        manager.markRevoked("Administrative Security Revocation")
        assertTrue(manager.isRevoked())
    }

    @Test
    fun testActiveCaseScoping() {
        val manager = DeviceIdentityManager()
        assertNull(manager.getActiveCaseId())

        manager.setActiveCaseId("CASE-UUID-999")
        assertEquals("CASE-UUID-999", manager.getActiveCaseId())

        manager.setActiveCaseId(null)
        assertNull(manager.getActiveCaseId())
    }
}
