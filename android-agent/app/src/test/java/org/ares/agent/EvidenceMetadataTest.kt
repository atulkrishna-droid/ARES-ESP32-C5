package org.ares.agent

import org.ares.agent.domain.model.EvidenceMetadata
import org.junit.Assert.*
import org.junit.Test
import java.security.MessageDigest
import java.util.UUID

class EvidenceMetadataTest {

    private fun computeSha256(input: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
        return digest.digest(input.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
    }

    private fun computeSha512(input: String): String {
        val digest = MessageDigest.getInstance("SHA-512")
        return digest.digest(input.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
    }

    @Test
    fun testEvidenceHashesAndMetadataStructure() {
        val rawArtifact = "INVENTORY_DUMP_HASH_INPUT"
        val sha256 = computeSha256(rawArtifact)
        val sha512 = computeSha512(rawArtifact)

        val evidence = EvidenceMetadata(
            evidenceId = UUID.randomUUID().toString(),
            caseId = "CASE-101",
            assessmentId = "ASSESS-202",
            sourceDeviceId = "ares-android-11223344",
            timestamp = "2026-09-27T14:00:00Z",
            artifactType = "SECURITY_POSTURE_REPORT",
            sha256 = sha256,
            sha512 = sha512,
            acquisitionMetadata = mapOf(
                "method" to "OFFICIAL_ANDROID_API",
                "rules_evaluated" to "5"
            )
        )

        assertEquals(64, evidence.sha256.length)
        assertEquals(128, evidence.sha512.length)
        assertEquals("CASE-101", evidence.caseId)
        assertEquals("ares-android-11223344", evidence.sourceDeviceId)
        assertEquals("5", evidence.acquisitionMetadata["rules_evaluated"])
    }
}
