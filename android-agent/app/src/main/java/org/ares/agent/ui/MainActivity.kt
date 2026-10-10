package org.ares.agent.ui

import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import org.ares.agent.R
import org.ares.agent.service.AresAgentService

/**
 * Main Activity providing transparent security diagnostics interface to device owner.
 *
 * Implements Section 1 & 10:
 * Displays device identity, active case authorization, and assessment execution trigger.
 */
class MainActivity : AppCompatActivity() {

    private val viewModel: MainViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val tvDeviceId = findViewById<TextView>(R.id.tvDeviceId)
        val tvState = findViewById<TextView>(R.id.tvState)
        val tvCapabilities = findViewById<TextView>(R.id.tvCapabilities)
        val tvFindings = findViewById<TextView>(R.id.tvFindings)
        val btnRunAssessment = findViewById<Button>(R.id.btnRunAssessment)

        // Start Foreground Service
        val serviceIntent = Intent(this, AresAgentService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent)
        } else {
            startService(serviceIntent)
        }

        lifecycleScope.launch {
            viewModel.identity.collectLatest { id ->
                tvDeviceId.text = "Device ID: ${id?.deviceId ?: "Unregistered"}"
            }
        }

        lifecycleScope.launch {
            viewModel.agentState.collectLatest { state ->
                tvState.text = "Status: ${state.name}"
                btnRunAssessment.isEnabled = state.canExecuteAssessment
            }
        }

        lifecycleScope.launch {
            viewModel.capabilities.collectLatest { caps ->
                if (caps != null) {
                    tvCapabilities.text = "Android ${caps.androidVersion} (API ${caps.sdkVersion}) | Patch: ${caps.securityPatch ?: "N/A"} | DevOptions: ${caps.developerOptionsStateIfAvailable}"
                }
            }
        }

        lifecycleScope.launch {
            viewModel.findings.collectLatest { findingsList ->
                if (findingsList.isEmpty()) {
                    tvFindings.text = "No active findings recorded."
                } else {
                    val sb = StringBuilder("Deterministic Findings (${findingsList.size}):\n\n")
                    for (f in findingsList) {
                        sb.append("[${f.severity}] ${f.ruleId}: ${f.title}\n")
                        sb.append("Details: ${f.description}\n\n")
                    }
                    tvFindings.text = sb.toString()
                }
            }
        }

        btnRunAssessment.setOnClickListener {
            val intent = Intent(this, AresAgentService::class.java).apply {
                action = "ACTION_RUN_ASSESSMENT"
            }
            startService(intent)
        }
    }
}
