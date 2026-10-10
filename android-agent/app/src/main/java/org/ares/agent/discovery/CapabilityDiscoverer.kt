package org.ares.agent.discovery

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import android.provider.Settings
import org.ares.agent.domain.model.DeviceCapabilities
import org.ares.agent.security.RedactingLogger

/**
 * Android Platform Capability Discoverer.
 *
 * Implements Section 3:
 * Discovers OS, SDK, network capabilities, developer options, and VPN state through official APIs.
 * Supports graceful execution in unit test / headless mock environments.
 */
class CapabilityDiscoverer(
    private val context: Context? = null
) {
    fun discoverCapabilities(): DeviceCapabilities {
        if (context == null) {
            // Unit test / Mock environment fallback
            return DeviceCapabilities(
                androidVersion = "14",
                sdkVersion = 34,
                securityPatch = "2026-08-01",
                deviceModel = "Pixel 8 Pro (Simulated)",
                manufacturer = "Google",
                appVersion = "1.0.0",
                networkCapabilities = listOf("WIFI", "INTERNET"),
                vpnStateIfAvailable = false,
                developerOptionsStateIfAvailable = false,
                debuggableStateIfAvailable = false,
                permissionsSupported = listOf("INTERNET", "ACCESS_NETWORK_STATE"),
                managementStateIfAvailable = "UNMANAGED",
                encryptionStatus = "ENCRYPTED"
            )
        }

        val androidVersion = Build.VERSION.RELEASE ?: "Unknown"
        val sdkVersion = Build.VERSION.SDK_INT
        val securityPatch = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            Build.VERSION.SECURITY_PATCH
        } else {
            null
        }

        val deviceModel = Build.MODEL ?: "Unknown"
        val manufacturer = Build.MANUFACTURER ?: "Unknown"

        // App version
        val appVersion = try {
            val pInfo = context.packageManager.getPackageInfo(context.packageName, 0)
            pInfo.versionName ?: "1.0.0"
        } catch (_: Exception) {
            "1.0.0"
        }

        // Network capabilities & VPN state
        val netCapsList = mutableListOf<String>()
        var vpnActive = false
        try {
            val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            val activeNetwork = cm?.activeNetwork
            val caps = cm?.getNetworkCapabilities(activeNetwork)
            if (caps != null) {
                if (caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) netCapsList.add("WIFI")
                if (caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)) netCapsList.add("CELLULAR")
                if (caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)) netCapsList.add("ETHERNET")
                if (caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN)) {
                    netCapsList.add("VPN")
                    vpnActive = true
                }
                if (caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)) netCapsList.add("INTERNET")
            }
        } catch (e: Exception) {
            RedactingLogger.w("CapabilityDiscoverer", "Failed to query network capabilities: ${e.message}")
        }

        // Developer Options & USB Debugging
        var devOptionsActive = false
        var usbDebuggingActive = false
        try {
            val devEnabled = Settings.Global.getInt(context.contentResolver, Settings.Global.DEVELOPMENT_SETTINGS_ENABLED, 0)
            devOptionsActive = (devEnabled == 1)
            val adbEnabled = Settings.Global.getInt(context.contentResolver, Settings.Global.ADB_ENABLED, 0)
            usbDebuggingActive = (adbEnabled == 1)
        } catch (_: Exception) {}

        // Debuggable flag of this app
        val isAppDebuggable = (context.applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0

        return DeviceCapabilities(
            androidVersion = androidVersion,
            sdkVersion = sdkVersion,
            securityPatch = securityPatch,
            deviceModel = deviceModel,
            manufacturer = manufacturer,
            appVersion = appVersion,
            networkCapabilities = netCapsList,
            vpnStateIfAvailable = vpnActive,
            developerOptionsStateIfAvailable = devOptionsActive,
            debuggableStateIfAvailable = usbDebuggingActive || isAppDebuggable,
            permissionsSupported = listOf("INTERNET", "ACCESS_NETWORK_STATE", "FOREGROUND_SERVICE"),
            managementStateIfAvailable = "UNMANAGED",
            encryptionStatus = "ENCRYPTED"
        )
    }
}
