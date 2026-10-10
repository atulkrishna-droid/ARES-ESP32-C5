package org.ares.agent

import org.ares.agent.domain.engine.SecurityPostureEngine
import org.ares.agent.domain.model.*
import org.junit.Assert.*
import org.junit.Test

class SecurityPostureEngineTest {

    private val engine = SecurityPostureEngine()

    @Test
    fun testOutdatedPatchGeneratesAndroidSec001() {
        val caps = DeviceCapabilities(
            androidVersion = "14",
            sdkVersion = 34,
            securityPatch = "2023-01-01", // Deliberately old patch
            deviceModel = "TestPhone",
            manufacturer = "TestCorp",
            appVersion = "1.0.0"
        )

        val findings = engine.evaluate(caps, emptyList())
        val patchFinding = findings.firstOrNull { it.ruleId == "ANDROID-SEC-001" }

        assertNotNull("Must report ANDROID-SEC-001 for outdated patch", patchFinding)
        assertEquals(FindingSeverity.MEDIUM, patchFinding?.severity)
        assertTrue(patchFinding?.description?.contains("exceeding") == true)
    }

    @Test
    fun testDebuggableAppGeneratesAppDebug001() {
        val caps = DeviceCapabilities(
            androidVersion = "14",
            sdkVersion = 34,
            securityPatch = "2026-08-01",
            deviceModel = "TestPhone",
            manufacturer = "TestCorp",
            appVersion = "1.0.0"
        )

        val apps = listOf(
            AppInventoryEntry(
                packageName = "com.vulnerable.debugapp",
                appName = "Vulnerable Debug App",
                versionName = "1.0",
                versionCode = 10,
                targetSdk = 34,
                minSdk = 26,
                isDebuggable = true,
                isSystemApp = false
            )
        )

        val findings = engine.evaluate(caps, apps)
        val debugFinding = findings.firstOrNull { it.ruleId == "APP-DEBUG-001" }

        assertNotNull("Must report APP-DEBUG-001 for debuggable app", debugFinding)
        assertEquals(FindingSeverity.MEDIUM, debugFinding?.severity)
        assertEquals("com.vulnerable.debugapp", debugFinding?.details?.get("packageName"))
    }

    @Test
    fun testSensitivePermissionGeneratesAppPerm001() {
        val caps = DeviceCapabilities(
            androidVersion = "14",
            sdkVersion = 34,
            securityPatch = "2026-08-01",
            deviceModel = "TestPhone",
            manufacturer = "TestCorp",
            appVersion = "1.0.0"
        )

        val apps = listOf(
            AppInventoryEntry(
                packageName = "com.unnecessary.camera",
                appName = "Flashlight App",
                versionName = "2.1",
                versionCode = 21,
                targetSdk = 34,
                minSdk = 26,
                isDebuggable = false,
                isSystemApp = false,
                permissions = listOf(
                    AppPermissionEntry(
                        permissionName = "android.permission.CAMERA",
                        protection = "dangerous",
                        granted = true
                    ),
                    AppPermissionEntry(
                        permissionName = "android.permission.READ_SMS",
                        protection = "dangerous",
                        granted = true
                    )
                )
            )
        )

        val findings = engine.evaluate(caps, apps)
        val permFinding = findings.firstOrNull { it.ruleId == "APP-PERM-001" }

        assertNotNull("Must report APP-PERM-001 for sensitive permissions", permFinding)
        assertEquals(FindingSeverity.MEDIUM, permFinding?.severity)
        assertTrue(permFinding?.details?.get("permissions")?.contains("android.permission.CAMERA") == true)
    }

    @Test
    fun testDeveloperOptionsGeneratesAndroidDev001() {
        val caps = DeviceCapabilities(
            androidVersion = "14",
            sdkVersion = 34,
            securityPatch = "2026-08-01",
            deviceModel = "TestPhone",
            manufacturer = "TestCorp",
            appVersion = "1.0.0",
            developerOptionsStateIfAvailable = true
        )

        val findings = engine.evaluate(caps, emptyList())
        val devFinding = findings.firstOrNull { it.ruleId == "ANDROID-DEV-001" }

        assertNotNull("Must report ANDROID-DEV-001 when developer options are enabled", devFinding)
        assertEquals(FindingSeverity.LOW, devFinding?.severity)
    }
}
