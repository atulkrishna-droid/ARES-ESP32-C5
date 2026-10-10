"""Report Generation Service for Professional Security Assessments."""
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.core.security import canonical_json_bytes, sha256_hash
from app.models.case import Case
from app.models.finding import Finding
from app.models.report import Report
from app.services.audit_service import AuditService


class ReportService:
    @classmethod
    def generate_report(
        cls,
        db: Session,
        target_id: str,
        actor_id: Optional[str] = None,
        format_type: str = "JSON",
        title: Optional[str] = None,
        generated_by: Optional[str] = None,
    ) -> Report:
        user_id = actor_id or generated_by
        if not user_id:
            raise ValueError("Generator user ID is required.")

        from app.models.assessment import Assessment
        assessment = db.query(Assessment).filter(Assessment.id == target_id).first()
        if assessment:
            case = db.query(Case).filter(Case.id == assessment.case_id).first()
            case_id = assessment.case_id
        else:
            case = db.query(Case).filter(Case.id == target_id).first()
            case_id = target_id

        if not case:
            raise ResourceNotFoundException("Case or Assessment not found.")

        # Aggregate case findings across all assessments
        findings_query = (
            db.query(Finding)
            .join(Assessment, Finding.assessment_id == Assessment.id)
            .filter(Assessment.case_id == case_id)
            .order_by(Finding.severity.desc(), Finding.created_at.asc())
            .all()
        )

        findings_data = []
        for f in findings_query:
            findings_data.append({
                "id": f.id,
                "rule_id": f.rule_id,
                "title": f.title,
                "severity": f.severity,
                "description": f.description,
                "recommendation": f.recommendation,
                "status": f.status,
                "evidence": f.evidence_json,
            })

        evidence_data = []
        for e in case.evidence_items:
            evidence_data.append({
                "id": e.id,
                "name": e.name,
                "type": e.type,
                "source": e.source,
                "sha256": e.sha256,
                "size_bytes": e.size_bytes,
                "collected_at": e.collected_at.isoformat(),
            })

        now = datetime.now(timezone.utc)
        report_title = title or f"ARES Security Assessment Report - {case.case_number}"

        report_payload: Dict[str, Any] = {
            "metadata": {
                "report_title": report_title,
                "case_number": case.case_number,
                "generated_at": now.isoformat(),
                "generated_by": user_id,
                "classification": "AUTHORIZED_SECURITY_ASSESSMENT",
            },
            "case": {
                "id": case.id,
                "title": case.title,
                "description": case.description,
                "status": case.status,
                "priority": case.priority,
            },
            "findings_summary": {
                "total": len(findings_data),
                "critical": sum(1 for f in findings_data if f["severity"] == "CRITICAL"),
                "high": sum(1 for f in findings_data if f["severity"] == "HIGH"),
                "medium": sum(1 for f in findings_data if f["severity"] == "MEDIUM"),
                "low": sum(1 for f in findings_data if f["severity"] == "LOW"),
                "info": sum(1 for f in findings_data if f["severity"] == "INFO"),
            },
            "findings": findings_data,
            "evidence_inventory": evidence_data,
        }

        # Generate HTML representation if requested or as alternate view
        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{report_title}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 2rem; }}
.card {{ background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; }}
h1, h2, h3 {{ color: #38bdf8; }}
.badge {{ padding: 0.25rem 0.5rem; border-radius: 4px; font-weight: bold; font-size: 0.8rem; display: inline-block; }}
.CRITICAL {{ background: #991b1b; color: #fecaca; }}
.HIGH {{ background: #c2410c; color: #ffedd5; }}
.MEDIUM {{ background: #854d0e; color: #fef08a; }}
.LOW {{ background: #166534; color: #bbf7d0; }}
.INFO {{ background: #1e40af; color: #dbeafe; }}
</style>
</head>
<body>
<h1>{report_title}</h1>
<div class="card">
    <p><strong>Case Number:</strong> {case.case_number}</p>
    <p><strong>Case Title:</strong> {case.title}</p>
    <p><strong>Generated At:</strong> {now.isoformat()}</p>
    <p><strong>Total Findings:</strong> {len(findings_data)}</p>
</div>
<h2>Findings Detail</h2>
"""
        for f in findings_data:
            html_content += f"""
<div class="card">
    <h3><span class="badge {f['severity']}">{f['severity']}</span> {f['title']}</h3>
    <p><strong>Rule ID:</strong> {f['rule_id']}</p>
    <p>{f['description']}</p>
    <p><strong>Recommendation:</strong> {f['recommendation']}</p>
</div>
"""
        html_content += "</body></html>"

        report_bytes = canonical_json_bytes(report_payload)
        report_sha256 = sha256_hash(report_bytes)

        report = Report(
            case_id=case.id,
            title=report_title,
            generated_by=user_id,
            format=format_type.upper(),
            content_json=report_payload,
            content_html=html_content if format_type.upper() in ("HTML", "BOTH") else None,
            sha256_hash=report_sha256,
            created_at=now,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        AuditService.record_event(
            db=db,
            action="REPORT_GENERATED",
            resource_type="REPORT",
            resource_id=report.id,
            actor_id=user_id,
            metadata={"case_id": case.id, "report_sha256": report_sha256, "findings_count": len(findings_data)},
        )
        return report
