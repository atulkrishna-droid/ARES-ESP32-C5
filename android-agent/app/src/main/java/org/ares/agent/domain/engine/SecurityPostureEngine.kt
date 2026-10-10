package org.ares.agent.domain.engine

import org.ares.agent.domain.model.AppInventoryEntry
import org.ares.agent.domain.model.DeviceCapabilities
import org.ares.agent.domain.model.FindingSeverity
import org.ares.agent.domain.model.SecurityFinding
import java.security.MessageDigest
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import java.util.UUID

/**
 * Deterministic Security Posture Evaluation Engine.
 *
 * Implements Section 5:
 * Evaluates device capabilities and application inventory against deterministic rules.
 * Does not make unsupported claims; produces concrete finding IDs, severities, and evidence references.
 */
class SecurityPostureEngine {

    companion object {
        const val ENGINE_VERSION = "1.0.0"
        private const val PATCH_MAX_AGE_DAYS = 90L
    }

    /**
     * Evaluates security posture across device configuration and application inventory.
     */
    fun evaluate(
        capabilities: DeviceCapabilities,
        applications: List<AppInventoryEntry>,
        timestamp: String = getCurrentIsoTimestamp()
    ): List<SecurityFinding> {
        val findings = mutableListOf<SecurityFinding>()

        // 1. Rule: ANDROID-SEC-001 (Outdated Android Security Patch)
        evaluateSecurityPatch(capabilities, timestamp)?.let { findings.add(it) }

        // 2. Rule: ANDROID-DEV-001 (Development / Debug Configuration Detected)
        evaluateDevelopmentState(capabilities, timestamp)?.let { findings.add(it) }

        // 3. Rule: NETWORK-SEC-001 (Potentially Weak Network Configuration)
        evaluateNetworkSecurity(capabilities, timestamp)?.let { findings.add(it) }

        // 4. Application-specific rules: APP-DEBUG-001 & APP-PERM-001
        for (app in applications) {
            // APP-DEBUG-001
            if (app.isDebuggable) {
                findings.add(
                    SecurityFinding(
                        findingId = "finding-${UUID.randomUUID().toString().take(8)}",
                        ruleId = "APP-DEBUG-001",
                        severity = FindingSeverity.MEDIUM,
                        title = "Debuggable Application Detected: ${app.appName}",
                        description = "The application '${app.packageName}' has android:debuggable enabled in its manifest, permitting runtime debugger attachment and memory dumping.",
                        evidenceReference = computeSha256("APP-DEBUG-001:${app.packageName}:${app.versionCode}"),
                        timestamp = timestamp,
                        ruleVersion = ENGINE_VERSION,
                        recommendation = "Recompile the release artifact with debuggable=false.",
                        details = mapOf(
                            "packageName" to app.packageName,
                            "versionCode" to app.versionCode.toString(),
                            "targetSdk" to app.targetSdk.toString()
                        )
                    )
                )
            }

            // APP-PERM-001 (Sensitive / Excessive Permissions)
            val dangerousPerms = app.permissions.filter { it.isDangerous && it.isGranted }
            if (dangerousPerms.isNotEmpty() && !app.isSystemApp) {
                val permList = dangerousPerms.joinToString(", ") { it.name }
                findings.add(
                    SecurityFinding(
                        findingId = "finding-${UUID.randomUUID().toString().take(8)}",
                        ruleId = "APP-PERM-001",
                        severity = FindingSeverity.MEDIUM,
                        title = "Sensitive Permissions Granted: ${app.appName}",
                        description = "The non-system application '${app.packageName}' has active grants for sensitive permissions: $permList.",
                        evidenceReference = computeSha256("APP-PERM-001:${app.packageName}:$permList"),
                        timestamp = timestamp,
                        ruleVersion = ENGINE_VERSION,
                        recommendation = "Review permission declarations against the principle of least privilege.",
                        details = mapOf(
                            "packageName" to app.packageName,
                            "grantedDangerousCount" to dangerousPerms.size.toString(),
                            "permissions" to permList
                        )
                    )
                )
            }
        }

        return findings
    }

    private fun evaluateSecurityPatch(caps: DeviceCapabilities, timestamp: String): SecurityFinding? {
        val patch = caps.securityPatch ?: return SecurityFinding(
            findingId = "finding-${UUID.randomUUID().toString().take(8)}",
            ruleId = "ANDROID-SEC-001",
            severity = FindingSeverity.HIGH,
            title = "Missing Platform Security Patch Information",
            description = "The Android platform did not report a valid security patch date string.",
            evidenceReference = computeSha256("ANDROID-SEC-001:NO_PATCH:${caps.androidVersion}"),
            timestamp = timestamp,
            ruleVersion = ENGINE_VERSION,
            recommendation = "Ensure the device is updated with official OEM firmware containing security bulletins.",
            details = mapOf("androidVersion" to caps.androidVersion)
        )

        try {
            val format = SimpleDateFormat("yyyy-MM-dd", Locale.US)
            val patchDate = format.parse(patch) ?: return null
            val now = Date()
            val diffDays = (now.time - patchDate.time) / (1000 * 60 * 60 * 24)

            if (diffDays > PATCH_MAX_AGE_DAYS) {
                return SecurityFinding(
                    findingId = "finding-${UUID.randomUUID().toString().take(8)}",
                    ruleId = "ANDROID-SEC-001",
                    severity = FindingSeverity.MEDIUM,
                    title = "Outdated Android Security Patch Level",
                    description = "Device security patch '$patch' is $diffDays days old, exceeding the 90-day compliance baseline.",
                    evidenceReference = computeSha256("ANDROID-SEC-001:$patch:$diffDays"),
                    timestamp = timestamp,
                    ruleVersion = ENGINE_VERSION,
                    recommendation = "Apply the latest Android platform security update from the vendor.",
                    details = mapOf(
                        "securityPatch" to patch,
                        "ageDays" to diffDays.toString(),
                        "thresholdDays" to PATCH_MAX_AGE_DAYS.toString()
                    )
                )
            }
        } catch (_: Exception) {
            // Unparseable format
        }
        return null
    }

    private fun evaluateDevelopmentState(caps: DeviceCapabilities, timestamp: String): SecurityFinding? {
        if (caps.developerOptionsStateIfAvailable || caps.debuggableStateIfAvailable) {
            return SecurityFinding(
                findingId = "finding-${UUID.randomUUID().toString().take(8)}",
                ruleId = "ANDROID-DEV-001",
                severity = FindingSeverity.LOW,
                title = "Development Options or USB Debugging Active",
                description = "Developer options or USB debugging are enabled on the host device. This expands the physical USB attack surface.",
                evidenceReference = computeSha256("ANDROID-DEV-001:DEV_OPTIONS:${caps.developerOptionsStateIfAvailable}"),
                timestamp = timestamp,
                ruleVersion = ENGINE_VERSION,
                recommendation = "Disable USB debugging and developer options outside authorized assessment workflows.",
                details = mapOf(
                    "developerOptions" to caps.developerOptionsStateIfAvailable.toString(),
                    "debuggable" to caps.debuggableStateIfAvailable.toString()
                )
            )
        }
        return null
    }

    private fun evaluateNetworkSecurity(caps: DeviceCapabilities, timestamp: String): SecurityFinding? {
        // If Wi-Fi is active but VPN is disabled on untrusted networks
        if (!caps.vpnStateIfAvailable && caps.networkCapabilities.contains("WIFI")) {
            return SecurityFinding(
                findingId = "finding-${UUID.randomUUID().toString().take(8)}",
                ruleId = "NETWORK-SEC-001",
                severity = FindingSeverity.LOW,
                title = "Wi-Fi Connection Without Active VPN",
                description = "The device is communicating over a wireless network interface without an active VPN tunnel.",
                evidenceReference = computeSha256("NETWORK-SEC-001:NO_VPN:WIFI"),
                timestamp = timestamp,
                ruleVersion = ENGINE_VERSION,
                recommendation = "Enable an encrypted VPN connection when operating on non-isolated wireless networks.",
                details = mapOf(
                    "networkCapabilities" to caps.networkCapabilities.joinToString(","),
                    "vpnActive" to "false"
                )
            )
        }
        return null
    }

    private fun computeSha256(input: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val bytes = digest.digest(input.toByteArray(Charsets.UTF_8))
        return bytes.joinToString("") { "%02x".format(it) }
    }

    private fun getCurrentIsoTimestamp(): String {
        val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        format.timeZone = TimeZone.getTimeZone("UTC")
        return format.format(Date())
    }
}
