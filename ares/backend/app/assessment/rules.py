"""Deterministic Rules Catalog for Security Assessments."""
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from app.core.constants import FindingCategory, FindingSeverity


@dataclass
class RuleDefinition:
    rule_id: str
    title: str
    description: str
    category: FindingCategory
    severity: FindingSeverity
    recommendation: str
    references: List[str]


RULES_CATALOG: Dict[str, RuleDefinition] = {
    "ANDROID-DEBUG-001": RuleDefinition(
        rule_id="ANDROID-DEBUG-001",
        title="USB Debugging Enabled",
        description=(
            "USB debugging (ADB) is enabled on the device. While standard in development environments, "
            "it expands the physical and host-based attack surface and should be restricted to authorized test workflows."
        ),
        category=FindingCategory.DEVICE_SECURITY,
        severity=FindingSeverity.LOW,
        recommendation="Disable USB debugging in Developer Options when not conducting authorized diagnostic sessions.",
        references=["https://developer.android.com/studio/debug/dev-options"],
    ),
    "APP-DEBUG-001": RuleDefinition(
        rule_id="APP-DEBUG-001",
        title="Debuggable Application Detected",
        description=(
            "An installed application has the android:debuggable flag set to true in its AndroidManifest. "
            "This allows external process attaching, memory inspection, and runtime manipulation."
        ),
        category=FindingCategory.APPLICATION_SECURITY,
        severity=FindingSeverity.MEDIUM,
        recommendation="Recompile the production APK with debugging disabled (android:debuggable='false').",
        references=["https://cwe.mitre.org/data/definitions/215.html"],
    ),
    "APP-PERM-001": RuleDefinition(
        rule_id="APP-PERM-001",
        title="Excessive or Sensitive Permissions Requested",
        description=(
            "An application has been granted high-risk permissions (e.g. Accessibility, SMS, Background Location, "
            "or Camera) that require security architecture review to ensure alignment with least privilege."
        ),
        category=FindingCategory.PERMISSIONS,
        severity=FindingSeverity.MEDIUM,
        recommendation="Audit declared application permissions and remove unnecessary dangerous permissions.",
        references=["https://developer.android.com/guide/topics/permissions/overview"],
    ),
    "WIFI-SEC-001": RuleDefinition(
        rule_id="WIFI-SEC-001",
        title="Unencrypted or Insecure Wi-Fi Network Detected",
        description=(
            "A wireless access point within radio frequency proximity is operating with OPEN authentication "
            "or deprecated WEP/WPA1 legacy encryption, leaving transmission susceptible to passive capture."
        ),
        category=FindingCategory.WIRELESS,
        severity=FindingSeverity.HIGH,
        recommendation="Upgrade the wireless environment to WPA3-SAE or enterprise WPA2 with strong pre-shared keys.",
        references=["https://www.wi-fi.org/discover-wi-fi/security"],
    ),
    "PATCH-LEVEL-001": RuleDefinition(
        rule_id="PATCH-LEVEL-001",
        title="Outdated Security Patch Level",
        description=(
            "The device's Android security patch level is older than the recommended 90-day compliance baseline, "
            "leaving known published platform vulnerabilities unmitigated."
        ),
        category=FindingCategory.CONFIGURATION,
        severity=FindingSeverity.MEDIUM,
        recommendation="Apply the latest Android platform security update from the device OEM.",
        references=["https://source.android.com/docs/security/bulletin"],
    ),
}
