package org.ares.agent

import org.ares.agent.discovery.CapabilityDiscoverer
import org.junit.Assert.*
import org.junit.Test

class CapabilityDiscoveryTest {

    @Test
    fun testHeadlessCapabilityDiscovery() {
        val discoverer = CapabilityDiscoverer(null)
        val caps = discoverer.discoverCapabilities()

        assertNotNull(caps.androidVersion)
        assertTrue(caps.sdkVersion >= 26)
        assertEquals("Google", caps.manufacturer)
        assertEquals("1.0.0", caps.appVersion)
        assertTrue(caps.networkCapabilities.contains("WIFI"))
        assertEquals("UNMANAGED", caps.managementStateIfAvailable)
        assertEquals("ENCRYPTED", caps.encryptionStatus)
    }
}
