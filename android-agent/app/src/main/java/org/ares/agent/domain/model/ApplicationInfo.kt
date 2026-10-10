package org.ares.agent.domain.model

import kotlinx.serialization.Serializable

/**
 * Declared and Granted Permission Model for an Application.
 */
@Serializable
data class AppPermissionEntry(
    val name: String = "",
    val protectionLevel: String = "normal",
    val isGranted: Boolean = false,
    val isDangerous: Boolean = false
) {
    // Convenience constructor
    constructor(
        permissionName: String,
        protection: String,
        granted: Boolean
    ) : this(
        name = permissionName,
        protectionLevel = protection,
        isGranted = granted,
        isDangerous = protection.contains("dangerous", ignoreCase = true) ||
                permissionName.contains("CAMERA", ignoreCase = true) ||
                permissionName.contains("LOCATION", ignoreCase = true) ||
                permissionName.contains("SMS", ignoreCase = true) ||
                permissionName.contains("CONTACTS", ignoreCase = true) ||
                permissionName.contains("RECORD_AUDIO", ignoreCase = true)
    )
}

/**
 * Application Inventory Entry.
 *
 * Implements Section 4:
 * Collects strictly authorized package metadata through official PackageManager APIs.
 */
@Serializable
data class AppInventoryEntry(
    val packageName: String,
    val appName: String,
    val versionName: String?,
    val versionCode: Long,
    val targetSdk: Int,
    val minSdk: Int,
    val isDebuggable: Boolean,
    val isSystemApp: Boolean,
    val installerPackageName: String? = null,
    val permissions: List<AppPermissionEntry> = emptyList()
)
