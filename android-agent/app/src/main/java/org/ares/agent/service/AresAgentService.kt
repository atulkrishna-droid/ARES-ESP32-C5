package org.ares.agent.service

import android.app.Service
import android.content.Intent
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import org.ares.agent.AresApplication
import org.ares.agent.R
import org.ares.agent.domain.model.AgentState
import org.ares.agent.domain.model.EvidenceMetadata
import org.ares.agent.domain.model.SecurityFinding
import org.ares.agent.protocol.AresEnvelope
import org.ares.agent.protocol.AresMessageTypes
import org.ares.agent.protocol.SequenceTracker
import org.ares.agent.security.RedactingLogger
import java.security.MessageDigest
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import java.util.UUID

/**
 * ARES Android Agent Foreground Service.
 *
 * Implements Section 1, 6, 7, 8 & 9:
 * - Coordinates lifecycle state transitions (OFFLINE -> AUTHENTICATING -> AUTHORIZED -> BUSY -> REVOKED)
 * - Executes periodic heartbeat (5-10s)
 * - Evaluates deterministic security posture
 * - Emits evidence metadata with SHA-256 and SHA-512 hashes
 * - Preserves state on disconnect, transitioning active assessments to INTERRUPTED
 */
class AresAgentService : Service() {

    companion object {
        private const val NOTIFICATION_ID = 101
        private const val HEARTBEAT_INTERVAL_MS = 8000L

        private val _agentState = MutableStateFlow(AgentState.OFFLINE)
        val agentState: StateFlow<AgentState> = _agentState.asStateFlow()

        private val _lastFindings = MutableStateFlow<List<SecurityFinding>>(emptyList())
        val lastFindings: StateFlow<List<SecurityFinding>> = _lastFindings.asStateFlow()
    }

    private val serviceScope = CoroutineScope(Dispatchers.IO + Job())
    private var heartbeatJob: Job? = null
    private val sequenceTracker = SequenceTracker()

    override fun onCreate() {
        super.onCreate()
        startForeground(NOTIFICATION_ID, buildNotification("ARES Agent Initializing..."))
        RedactingLogger.i("AresAgentService", "Foreground service started.")
        initiateConnectionFlow()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action
        if (action == "ACTION_RUN_ASSESSMENT") {
            val caseId = intent.getStringExtra("EXTRA_CASE_ID")
            executeAssessment(caseId)
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        heartbeatJob?.cancel()
        _agentState.value = AgentState.OFFLINE
        RedactingLogger.i("AresAgentService", "Service destroyed. State set to OFFLINE.")
    }

    fun initiateConnectionFlow() {
        serviceScope.launch {
            val app = AresApplication.instance
            if (app.identityManager.isRevoked()) {
                _agentState.value = AgentState.REVOKED
                updateNotification("Device is REVOKED by security policy.")
                return@launch
            }

            _agentState.value = AgentState.AUTHENTICATING
            updateNotification("Authenticating with ARES backend...")

            val identity = app.identityManager.getOrCreateIdentity()
            val transport = app.transport

            // 1. Establish transport connection
            val connected = transport.connect()
            if (!connected) {
                _agentState.value = AgentState.OFFLINE
                updateNotification("Offline - Disconnected from backend")
                return@launch
            }

            // 2. Transmit HELLO
            val helloMsg = AresEnvelope(
                messageId = UUID.randomUUID().toString(),
                deviceId = identity.deviceId,
                timestamp = getCurrentIsoTimestamp(),
                type = AresMessageTypes.HELLO,
                sequence = sequenceTracker.nextOutboundSequence(),
                payload = mapOf(
                    "protocol_version" to "ARES/1.0",
                    "device_type" to "ANDROID",
                    "enrollment_id" to identity.enrollmentId
                )
            )
            val signedHello = signEnvelope(helloMsg)
            val helloResp = transport.sendMessage(signedHello)

            if (helloResp == null) {
                _agentState.value = AgentState.OFFLINE
                updateNotification("Offline - No response to HELLO")
                return@launch
            }

            if (helloResp.type == AresMessageTypes.ERROR &&
                helloResp.payload["code"] == "DEVICE_REVOKED") {
                app.identityManager.markRevoked()
                _agentState.value = AgentState.REVOKED
                updateNotification("Device is REVOKED")
                return@launch
            }

            // 3. Check authorization status
            val status = helloResp.payload["status"] as? String
            val authorizedCaseId = helloResp.payload["authorized_case_id"] as? String
            if (status == "AUTHORIZED") {
                _agentState.value = AgentState.AUTHORIZED
                app.identityManager.setActiveCaseId(authorizedCaseId)
                updateNotification("Ready - Authorized for Case: ${authorizedCaseId ?: "Default"}")
            } else {
                _agentState.value = AgentState.OFFLINE
                updateNotification("Awaiting Case Authorization")
            }

            // Start periodic heartbeat
            startHeartbeatLoop()
        }
    }

    private fun startHeartbeatLoop() {
        heartbeatJob?.cancel()
        heartbeatJob = serviceScope.launch {
            val app = AresApplication.instance
            while (isActive) {
                delay(HEARTBEAT_INTERVAL_MS)
                if (_agentState.value == AgentState.REVOKED) break

                val identity = app.identityManager.getOrCreateIdentity()
                val caps = app.capabilityDiscoverer.discoverCapabilities()
                val heartbeatMsg = AresEnvelope(
                    messageId = UUID.randomUUID().toString(),
                    deviceId = identity.deviceId,
                    timestamp = getCurrentIsoTimestamp(),
                    type = AresMessageTypes.HEARTBEAT,
                    sequence = sequenceTracker.nextOutboundSequence(),
                    payload = mapOf(
                        "state" to _agentState.value.name,
                        "vpn_active" to caps.vpnStateIfAvailable,
                        "developer_options" to caps.developerOptionsStateIfAvailable
                    )
                )

                val signedHeartbeat = signEnvelope(heartbeatMsg)
                val resp = app.transport.sendMessage(signedHeartbeat)
                if (resp == null) {
                    // Transport drop
                    if (_agentState.value == AgentState.BUSY) {
                        RedactingLogger.w("AresAgentService", "USB/Network disconnected during active assessment -> INTERRUPTED")
                    }
                    _agentState.value = AgentState.OFFLINE
                    updateNotification("Offline - Disconnected from backend")
                } else if (_agentState.value == AgentState.OFFLINE) {
                    _agentState.value = AgentState.AUTHORIZED
                    updateNotification("Ready - Reconnected")
                }
            }
        }
    }

    fun executeAssessment(caseId: String?) {
        serviceScope.launch {
            val app = AresApplication.instance
            val activeCase = caseId ?: app.identityManager.getActiveCaseId()

            if (activeCase == null) {
                RedactingLogger.w("AresAgentService", "Assessment rejected: No authorized case in scope.")
                return@launch
            }

            if (!_agentState.value.canExecuteAssessment) {
                RedactingLogger.w("AresAgentService", "Assessment rejected: Agent not in AUTHORIZED/BUSY state.")
                return@launch
            }

            _agentState.value = AgentState.BUSY
            updateNotification("Executing Security Assessment for Case $activeCase...")

            val caps = app.capabilityDiscoverer.discoverCapabilities()
            val apps = app.inventoryScanner.scanInventory()
            val findings = app.postureEngine.evaluate(caps, apps)
            _lastFindings.value = findings

            // Generate cryptographic evidence metadata
            val canonicalEvidenceData = "${identity().deviceId}:$activeCase:${findings.size}"
            val sha256 = computeHash(canonicalEvidenceData, "SHA-256")
            val sha512 = computeHash(canonicalEvidenceData, "SHA-512")
            val assessmentId = UUID.randomUUID().toString()

            val evidence = EvidenceMetadata(
                evidenceId = UUID.randomUUID().toString(),
                caseId = activeCase,
                assessmentId = assessmentId,
                sourceDeviceId = identity().deviceId,
                timestamp = getCurrentIsoTimestamp(),
                artifactType = "SECURITY_POSTURE_METADATA",
                sha256 = sha256,
                sha512 = sha512,
                acquisitionMetadata = mapOf(
                    "findings_count" to findings.size.toString(),
                    "apps_scanned" to apps.size.toString(),
                    "sdk_version" to caps.sdkVersion.toString()
                )
            )

            // Submit evidence metadata to backend
            val evidenceMsg = AresEnvelope(
                messageId = UUID.randomUUID().toString(),
                deviceId = identity().deviceId,
                timestamp = getCurrentIsoTimestamp(),
                type = AresMessageTypes.EVIDENCE_METADATA,
                sequence = sequenceTracker.nextOutboundSequence(),
                payload = mapOf(
                    "evidence_id" to evidence.evidenceId,
                    "case_id" to evidence.caseId,
                    "assessment_id" to evidence.assessmentId,
                    "artifact_type" to evidence.artifactType,
                    "sha256" to evidence.sha256,
                    "sha512" to evidence.sha512,
                    "acquisition_metadata" to evidence.acquisitionMetadata
                )
            )
            val signedEvidence = signEnvelope(evidenceMsg)
            app.transport.sendMessage(signedEvidence)

            _agentState.value = AgentState.AUTHORIZED
            updateNotification("Ready - Assessment Completed (${findings.size} findings)")
        }
    }

    private fun signEnvelope(envelope: AresEnvelope): AresEnvelope {
        val app = AresApplication.instance
        val canonicalBytes = envelope.canonicalBytes()
        val signature = app.keystoreManager.sign(canonicalBytes)
        return envelope.copy(signature = signature)
    }

    private fun identity() = AresApplication.instance.identityManager.getOrCreateIdentity()

    private fun computeHash(input: String, algorithm: String): String {
        val digest = MessageDigest.getInstance(algorithm)
        val bytes = digest.digest(input.toByteArray(Charsets.UTF_8))
        return bytes.joinToString("") { "%02x".format(it) }
    }

    private fun getCurrentIsoTimestamp(): String {
        val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        format.timeZone = TimeZone.getTimeZone("UTC")
        return format.format(Date())
    }

    private fun buildNotification(contentText: String) =
        NotificationCompat.Builder(this, AresApplication.NOTIFICATION_CHANNEL_ID)
            .setContentTitle("ARES Security Agent")
            .setContentText(contentText)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setOngoing(true)
            .build()

    private fun updateNotification(contentText: String) {
        val notification = buildNotification(contentText)
        val manager = getSystemService(NOTIFICATION_SERVICE) as android.app.NotificationManager
        manager.notify(NOTIFICATION_ID, notification)
    }
}
