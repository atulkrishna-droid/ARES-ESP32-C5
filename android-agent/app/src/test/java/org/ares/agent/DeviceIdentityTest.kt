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

        // Verify persistence: second call yields identical device ID
        val id2 = manager.getOrCreateIdentity()
        assertEquals(id1.deviceId, id2.deviceId)
        assertEquals(id1.enrollmentId, id2.enrollmentId)
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
