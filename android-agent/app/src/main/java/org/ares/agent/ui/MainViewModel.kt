package org.ares.agent.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.ares.agent.AresApplication
import org.ares.agent.domain.model.AgentState
import org.ares.agent.domain.model.DeviceCapabilities
import org.ares.agent.domain.model.DeviceIdentity
import org.ares.agent.domain.model.SecurityFinding
import org.ares.agent.service.AresAgentService

/**
 * Main Activity ViewModel.
 *
 * Implements Jetpack MVVM pattern connecting UI with domain and background service state.
 */
class MainViewModel : ViewModel() {

    private val app = AresApplication.instance

    val agentState: StateFlow<AgentState> = AresAgentService.agentState
    val findings: StateFlow<List<SecurityFinding>> = AresAgentService.lastFindings

    private val _identity = MutableStateFlow<DeviceIdentity?>(null)
    val identity: StateFlow<DeviceIdentity?> = _identity.asStateFlow()

    private val _capabilities = MutableStateFlow<DeviceCapabilities?>(null)
    val capabilities: StateFlow<DeviceCapabilities?> = _capabilities.asStateFlow()

    init {
        loadDeviceData()
    }

    fun loadDeviceData() {
        viewModelScope.launch {
            _identity.value = app.identityManager.getOrCreateIdentity()
            _capabilities.value = app.capabilityDiscoverer.discoverCapabilities()
        }
    }

    fun executeAssessment(caseId: String? = null) {
        viewModelScope.launch {
            val caps = app.capabilityDiscoverer.discoverCapabilities()
            val apps = app.inventoryScanner.scanInventory()
            app.postureEngine.evaluate(caps, apps)
        }
    }
}
