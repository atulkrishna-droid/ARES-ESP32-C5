"""Deterministic Assessment Evaluation Engine."""
from typing import Any
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app.assessment.rules import RULES_CATALOG
from app.core.constants import AssessmentStatus, FindingStatus
from app.core.exceptions import (
    DeviceNotAuthorizedException,
    ResourceNotFoundException,
    ScopeViolationException,
)
from app.models.android_device import AndroidDevice
from app.models.application import Application
from app.models.assessment import Assessment
from app.models.device import Device
from app.models.finding import Finding
from app.models.wifi_network import WifiNetwork
from app.services.audit_service import AuditService
from app.services.device_service import DeviceService


class AssessmentEngine:
    @classmethod
    def create_assessment(
        cls,
        db: Session,
        request: Optional[Any] = None,
        creator_id: Optional[str] = None,
        data: Optional[Any] = None,
    ) -> Assessment:
        from app.models.case import Case
        req = request or data
        if not req:
            raise ValueError("Assessment create request is required.")

        case = db.query(Case).filter(Case.id == req.case_id).first()
        if not case:
            raise ResourceNotFoundException("Target Case not found.")

        device = db.query(Device).filter(Device.id == req.target_device_id).first()
        if not device:
            raise ResourceNotFoundException("Target Device not found.")

        scope_dict = req.get_effective_scope() if hasattr(req, "get_effective_scope") else (getattr(req, "scope_json", None) or getattr(req, "scope", None) or {})
        atype = req.assessment_type.value if hasattr(req.assessment_type, "value") else str(req.assessment_type)

        assessment = Assessment(
            case_id=case.id,
            target_device_id=device.id,
            assessment_type=atype,
            status=AssessmentStatus.CREATED.value,
            scope_json=scope_dict,
            created_by=creator_id,
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        AuditService.record_event(
            db=db,
            action="ASSESSMENT_CREATED",
            resource_type="ASSESSMENT",
            resource_id=assessment.id,
            actor_id=creator_id,
            metadata={"case_id": case.id, "target_device_id": device.id},
        )
        return assessment

    @classmethod
    def start_assessment(cls, db: Session, assessment_id: str, actor_id: str) -> Assessment:
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise ResourceNotFoundException("Assessment not found.")

        # Strict Case-Scope & Device Authorization verification
        from app.models.case import Case
        from app.models.device import DeviceAuthorization

        case = db.query(Case).filter(Case.id == assessment.case_id).first()
        if not case:
            raise ResourceNotFoundException("Assessment Case not found.")

        target_device = db.query(Device).filter(Device.id == assessment.target_device_id).first()
        if not target_device:
            raise ResourceNotFoundException("Target device not found.")

        now = datetime.now(timezone.utc)
        active_auth = db.query(DeviceAuthorization).filter(
            DeviceAuthorization.device_id == target_device.id,
            DeviceAuthorization.case_id == assessment.case_id,
            DeviceAuthorization.status == "ACTIVE",
        ).first()

        if not active_auth:
            raise DeviceNotAuthorizedException(
                f"Device '{target_device.device_uuid}' does not have an ACTIVE authorization for Case '{case.case_number}'."
            )

        if active_auth.expires_at:
            exp_at = active_auth.expires_at
            if exp_at.tzinfo is None:
                exp_at = exp_at.replace(tzinfo=timezone.utc)
            if exp_at < now:
                active_auth.status = "EXPIRED"
                db.commit()
                raise DeviceNotAuthorizedException(
                    f"Device authorization for Case '{case.case_number}' has expired."
                )

        # Check assessment scope expiry
        scope = assessment.scope_json or {}
        scope_expires_str = scope.get("expires_at")
        if scope_expires_str:
            try:
                scope_expires_dt = datetime.fromisoformat(scope_expires_str.replace("Z", "+00:00"))
                if scope_expires_dt < now:
                    raise ScopeViolationException("Assessment scope has expired.")
            except ValueError:
                pass

        # Acquire concurrency lock
        DeviceService.acquire_device_lock(db, target_device.id, assessment.id)

        assessment.status = AssessmentStatus.RUNNING.value
        assessment.started_at = now
        db.commit()
        db.refresh(assessment)

        AuditService.record_event(
            db=db,
            action="ASSESSMENT_STARTED",
            resource_type="ASSESSMENT",
            resource_id=assessment.id,
            actor_id=actor_id,
            metadata={"target_device_id": target_device.id, "type": assessment.assessment_type},
        )
        return assessment

    @classmethod
    def run_evaluation(cls, db: Session, assessment_id: str, actor_id: str) -> List[Finding]:
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise ResourceNotFoundException("Assessment not found.")

        device = db.query(Device).filter(Device.id == assessment.target_device_id).first()
        if not device:
            raise ResourceNotFoundException("Target device not found.")

        findings_created: List[Finding] = []
        now = datetime.now(timezone.utc)

        # Scope validation
        scope = assessment.scope_json or {}
        allowed_ops = set(scope.get("allowed_operations", ["*"]))

        # 1. Evaluate Android OS Posture
        android_data = db.query(AndroidDevice).filter(AndroidDevice.device_id == device.id).first()
        if android_data and ("*" in allowed_ops or "SECURITY_POSTURE" in allowed_ops):
            if android_data.usb_debugging_status:
                rule = RULES_CATALOG["ANDROID-DEBUG-001"]
                f = Finding(
                    assessment_id=assessment.id,
                    rule_id=rule.rule_id,
                    device_id=device.id,
                    severity=rule.severity.value,
                    title=rule.title,
                    description=rule.description,
                    evidence_json={"usb_debugging_status": True, "sdk_version": android_data.sdk_version},
                    recommendation=rule.recommendation,
                    status=FindingStatus.OPEN.value,
                    created_at=now,
                )
                db.add(f)
                findings_created.append(f)

        # 2. Evaluate Installed Applications
        if "*" in allowed_ops or "APPLICATION_INVENTORY" in allowed_ops:
            apps = db.query(Application).filter(Application.device_id == device.id).all()
            for app_item in apps:
                if app_item.debuggable:
                    rule = RULES_CATALOG["APP-DEBUG-001"]
                    f = Finding(
                        assessment_id=assessment.id,
                        rule_id=rule.rule_id,
                        device_id=device.id,
                        application_id=app_item.id,
                        severity=rule.severity.value,
                        title=f"{rule.title}: {app_item.app_name}",
                        description=rule.description,
                        evidence_json={
                            "package_name": app_item.package_name,
                            "debuggable": True,
                            "target_sdk": app_item.target_sdk,
                        },
                        recommendation=rule.recommendation,
                        status=FindingStatus.OPEN.value,
                        created_at=now,
                    )
                    db.add(f)
                    findings_created.append(f)

                # Sensitive permissions check
                for p in app_item.permissions:
                    if p.assessment_result == "REVIEW_REQUIRED":
                        rule = RULES_CATALOG["APP-PERM-001"]
                        f = Finding(
                            assessment_id=assessment.id,
                            rule_id=rule.rule_id,
                            device_id=device.id,
                            application_id=app_item.id,
                            severity=rule.severity.value,
                            title=f"Sensitive Permission: {p.permission_name}",
                            description=f"App '{app_item.app_name}' holds high-privilege permission '{p.permission_name}'.",
                            evidence_json={"package_name": app_item.package_name, "permission": p.permission_name},
                            recommendation=rule.recommendation,
                            status=FindingStatus.OPEN.value,
                            created_at=now,
                        )
                        db.add(f)
                        findings_created.append(f)

        # 3. Evaluate Wi-Fi Observations
        if "*" in allowed_ops or "WIFI_DISCOVERY" in allowed_ops:
            wifi_records = db.query(WifiNetwork).filter(WifiNetwork.assessment_id == assessment.id).all()
            for w in wifi_records:
                if w.security_type.upper() in ("OPEN", "WEP"):
                    rule = RULES_CATALOG["WIFI-SEC-001"]
                    f = Finding(
                        assessment_id=assessment.id,
                        rule_id=rule.rule_id,
                        device_id=device.id,
                        severity=rule.severity.value,
                        title=f"{rule.title}: {w.ssid or '<HIDDEN>'}",
                        description=f"Access point on channel {w.channel} ({w.band}) operates with '{w.security_type}' security.",
                        evidence_json={
                            "ssid": w.ssid,
                            "bssid_hash": w.bssid_hash,
                            "security_type": w.security_type,
                            "channel": w.channel,
                            "frequency": w.frequency,
                            "band": w.band,
                        },
                        recommendation=rule.recommendation,
                        status=FindingStatus.OPEN.value,
                        created_at=now,
                    )
                    db.add(f)
                    findings_created.append(f)

        # Finalize assessment
        assessment.status = AssessmentStatus.COMPLETED.value
        assessment.completed_at = now
        DeviceService.release_device_lock(db, device.id)

        db.commit()

        AuditService.record_event(
            db=db,
            action="ASSESSMENT_COMPLETED",
            resource_type="ASSESSMENT",
            resource_id=assessment.id,
            actor_id=actor_id,
            metadata={"findings_count": len(findings_created)},
        )
        return findings_created

    @classmethod
    def stop_assessment(cls, db: Session, assessment_id: str, actor_id: str) -> Assessment:
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise ResourceNotFoundException("Assessment not found.")

        assessment.status = AssessmentStatus.COMPLETED.value
        assessment.completed_at = datetime.now(timezone.utc)
        DeviceService.release_device_lock(db, assessment.target_device_id)
        db.commit()
        db.refresh(assessment)

        AuditService.record_event(
            db=db,
            action="ASSESSMENT_STOPPED",
            resource_type="ASSESSMENT",
            resource_id=assessment.id,
            actor_id=actor_id,
            metadata={},
        )
        return assessment
