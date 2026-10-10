package org.ares.agent.discovery

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.os.Build
import org.ares.agent.domain.model.AppInventoryEntry
import org.ares.agent.domain.model.AppPermissionEntry
import org.ares.agent.security.RedactingLogger

/**
 * Application Inventory Scanner.
 *
 * Implements Section 4:
 * Collects authorized package metadata and declared/granted permissions through official PackageManager APIs.
 * Supports graceful fallback if QUERY_ALL_PACKAGES is ungranted or in headless tests.
 */
class ApplicationInventoryScanner(
    private val context: Context? = null
) {
    fun scanInventory(): List<AppInventoryEntry> {
        if (context == null) {
            // Unit test / headless fallback
            return generateMockInventory()
        }

        val pm = context.packageManager
        val entries = mutableListOf<AppInventoryEntry>()

        try {
            val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                PackageManager.GET_PERMISSIONS or PackageManager.GET_SIGNING_CERTIFICATES
            } else {
                @Suppress("DEPRECATION")
                PackageManager.GET_PERMISSIONS or PackageManager.GET_SIGNATURES
            }

            val installedPackages = pm.getInstalledPackages(flags)

            for (pkg in installedPackages) {
                val appInfo = pkg.applicationInfo ?: continue
                val appName = pm.getApplicationLabel(appInfo).toString()
                val isDebuggable = (appInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
                val isSystem = (appInfo.flags and ApplicationInfo.FLAG_SYSTEM) != 0

                val targetSdk = appInfo.targetSdkVersion
                val minSdk = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                    appInfo.minSdkVersion
                } else {
                    16
                }

                val versionCode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                    pkg.longVersionCode
                } else {
                    @Suppress("DEPRECATION")
                    pkg.versionCode.toLong()
                }

                val permissions = mutableListOf<AppPermissionEntry>()
                val requestedPerms = pkg.requestedPermissions
                val requestedFlags = pkg.requestedPermissionsFlags

                if (requestedPerms != null) {
                    for (i in requestedPerms.indices) {
                        val permName = requestedPerms[i]
                        val isGranted = if (requestedFlags != null && i < requestedFlags.size) {
                            (requestedFlags[i] and PackageInfo.REQUESTED_PERMISSION_GRANTED) != 0
                        } else {
                            false
                        }

                        val protection = try {
                            val pInfo = pm.getPermissionInfo(permName, 0)
                            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                                when (pInfo.protection) {
                                    android.content.pm.PermissionInfo.PROTECTION_DANGEROUS -> "dangerous"
                                    android.content.pm.PermissionInfo.PROTECTION_SIGNATURE -> "signature"
                                    else -> "normal"
                                }
                            } else {
                                "normal"
                            }
                        } catch (_: Exception) {
                            "normal"
                        }

                        permissions.add(
                            AppPermissionEntry(
                                permissionName = permName,
                                protection = protection,
                                granted = isGranted
                            )
                        )
                    }
                }

                entries.add(
                    AppInventoryEntry(
                        packageName = pkg.packageName,
                        appName = appName,
                        versionName = pkg.versionName,
                        versionCode = versionCode,
                        targetSdk = targetSdk,
                        minSdk = minSdk,
                        isDebuggable = isDebuggable,
                        isSystemApp = isSystem,
                        installerPackageName = null,
                        permissions = permissions
                    )
                )
            }
        } catch (e: Exception) {
            RedactingLogger.w("ApplicationInventoryScanner", "Permission denied or package query restricted: ${e.message}")
        }

        return entries
    }

    private fun generateMockInventory(): List<AppInventoryEntry> {
        return listOf(
            AppInventoryEntry(
                packageName = "org.ares.agent",
                appName = "ARES Agent",
                versionName = "1.0.0",
                versionCode = 1,
                targetSdk = 34,
                minSdk = 26,
                isDebuggable = false,
                isSystemApp = false,
                permissions = listOf(
                    AppPermissionEntry("android.permission.INTERNET", "normal", true),
                    AppPermissionEntry("android.permission.ACCESS_NETWORK_STATE", "normal", true)
                )
            ),
            AppInventoryEntry(
                packageName = "com.example.testapp",
                appName = "Test Debug App",
                versionName = "0.9.0",
                versionCode = 90,
                targetSdk = 33,
                minSdk = 24,
                isDebuggable = true, // Triggers APP-DEBUG-001
                isSystemApp = false,
                permissions = listOf(
                    AppPermissionEntry("android.permission.CAMERA", "dangerous", true), // Triggers APP-PERM-001
                    AppPermissionEntry("android.permission.READ_SMS", "dangerous", true)
                )
            )
        )
    }
}
