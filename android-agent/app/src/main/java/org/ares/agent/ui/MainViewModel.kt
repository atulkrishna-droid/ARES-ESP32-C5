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
import org.ares.agent.security.LegacyDeviceIdentityException

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

    private val _identityError = MutableStateFlow<String?>(null)
    val identityError: StateFlow<String?> = _identityError.asStateFlow()

    private val _capabilities = MutableStateFlow<DeviceCapabilities?>(null)
    val capabilities: StateFlow<DeviceCapabilities?> = _capabilities.asStateFlow()

    init {
        loadDeviceData()
    }

    fun loadDeviceData() {
        viewModelScope.launch {
            try {
                _identity.value = app.identityManager.getOrCreateIdentity()
                _identityError.value = null
                _capabilities.value = app.capabilityDiscoverer.discoverCapabilities()
            } catch (legacy: LegacyDeviceIdentityException) {
                _identity.value = null
                _identityError.value = "Legacy device identity requires operator review. No replacement was created."
            } catch (_: Exception) {
                _identity.value = null
                _identityError.value = "Device identity could not be loaded or saved. No handshake was sent."
            }
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
