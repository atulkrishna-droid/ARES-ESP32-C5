"""Security Findings Endpoints."""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_permission
from app.core.database import get_db
from app.models.finding import Finding
from app.models.user import User
from app.schemas.assessment import FindingResponse, FindingUpdateRequest

router = APIRouter(prefix="/findings", tags=["Findings"])


@router.get("", response_model=List[FindingResponse], dependencies=[Depends(require_permission("assessment.read"))])
def list_findings(
    assessment_id: Optional[str] = None,
    device_id: Optional[str] = None,
    severity: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(Finding)
    if assessment_id:
        query = query.filter(Finding.assessment_id == assessment_id)
    if device_id:
        query = query.filter(Finding.device_id == device_id)
    if severity:
        query = query.filter(Finding.severity == severity.upper())
    return query.order_by(Finding.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{finding_id}", response_model=FindingResponse, dependencies=[Depends(require_permission("assessment.read"))])
def get_finding(finding_id: str, db: Session = Depends(get_db)):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")
    return finding


@router.patch("/{finding_id}", response_model=FindingResponse, dependencies=[Depends(require_permission("assessment.write"))])
def update_finding(
    finding_id: str,
    request: FindingUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")

    finding.status = request.status.value
    if request.status.value in ("RESOLVED", "ACCEPTED_RISK", "FALSE_POSITIVE"):
        finding.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(finding)
    return finding
