package org.ares.agent.domain.model

import kotlinx.serialization.Serializable

/**
 * Android Device Capability Model.
 *
 * Implements Section 3:
 * Reports only legitimate platform capabilities without bypassing permissions.
 */
@Serializable
data class DeviceCapabilities(
    val androidVersion: String,
    val sdkVersion: Int,
    val securityPatch: String?,
    val deviceModel: String,
    val manufacturer: String,
    val appVersion: String,
    val networkCapabilities: List<String> = emptyList(),
    val vpnStateIfAvailable: Boolean = false,
    val developerOptionsStateIfAvailable: Boolean = false,
    val debuggableStateIfAvailable: Boolean = false,
    val permissionsSupported: List<String> = emptyList(),
    val managementStateIfAvailable: String = "UNMANAGED",
    val encryptionStatus: String = "ENCRYPTED"
)
