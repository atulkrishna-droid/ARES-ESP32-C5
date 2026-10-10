package org.ares.agent

import org.ares.agent.discovery.ApplicationInventoryScanner
import org.junit.Assert.*
import org.junit.Test

class ApplicationInventoryTest {

    @Test
    fun testHeadlessInventoryScan() {
        val scanner = ApplicationInventoryScanner(null)
        val apps = scanner.scanInventory()

        assertTrue("Inventory must not be empty", apps.isNotEmpty())
        val aresApp = apps.firstOrNull { it.packageName == "org.ares.agent" }
        assertNotNull("Must include ARES Agent self-entry", aresApp)
        assertFalse("Production ARES agent must not be debuggable", aresApp?.isDebuggable ?: true)

        val debugApp = apps.firstOrNull { it.isDebuggable }
        assertNotNull("Mock inventory provides sample debuggable app", debugApp)
        assertTrue(debugApp?.permissions?.any { it.isDangerous } == true)
    }
}
