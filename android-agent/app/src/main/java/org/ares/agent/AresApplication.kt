package org.ares.agent

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import org.ares.agent.discovery.ApplicationInventoryScanner
import org.ares.agent.discovery.CapabilityDiscoverer
import org.ares.agent.domain.engine.SecurityPostureEngine
import org.ares.agent.security.DeviceIdentityManager
import org.ares.agent.security.KeystoreManager
import org.ares.agent.security.RedactingLogger
import org.ares.agent.security.SharedPreferencesIdentityStore
import org.ares.agent.transport.AresTransport
import org.ares.agent.transport.HttpTransport

/**
 * ARES Android Agent Application Entrypoint.
 *
 * Implements Section 1 & 10:
 * Initializes security subsystem, notification channels, and central dependency instances.
 */
class AresApplication : Application() {

    companion object {
        const val NOTIFICATION_CHANNEL_ID = "ares_agent_service_channel"
        lateinit var instance: AresApplication
            private set
    }

    val keystoreManager by lazy { KeystoreManager() }
    val identityManager by lazy {
        DeviceIdentityManager(
            keystoreManager = keystoreManager,
            persistentStore = SharedPreferencesIdentityStore(
                getSharedPreferences("ares_identity", Context.MODE_PRIVATE)
            )
        )
    }
    val capabilityDiscoverer by lazy { CapabilityDiscoverer(this) }
    val inventoryScanner by lazy { ApplicationInventoryScanner(this) }
    val postureEngine by lazy { SecurityPostureEngine() }
    val transport: AresTransport by lazy { HttpTransport() }

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()
        RedactingLogger.i("AresApplication", "ARES Agent application initialized.")
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = getString(R.string.channel_name)
            val descriptionText = getString(R.string.channel_description)
            val importance = NotificationManager.IMPORTANCE_LOW
            val channel = NotificationChannel(NOTIFICATION_CHANNEL_ID, name, importance).apply {
                description = descriptionText
            }
            val notificationManager: NotificationManager =
                getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }
}
