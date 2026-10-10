"""Tamper-Evident Audit Log and Chain Verification Endpoints."""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps import require_permission
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogResponse, AuditVerificationResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit Log"])


@router.get("", response_model=List[AuditLogResponse], dependencies=[Depends(require_permission("audit.read"))])
def list_audit_logs(
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type.upper())
    if action:
        query = query.filter(AuditLog.action == action.upper())
    return query.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).offset(skip).limit(limit).all()


@router.get("/verify", response_model=AuditVerificationResponse, dependencies=[Depends(require_permission("audit.read"))])
def verify_audit_log_integrity(db: Session = Depends(get_db)):
    is_valid, total_events, invalid_id, last_verified = AuditService.verify_chain(db)
    return AuditVerificationResponse(
        valid=is_valid,
        total_events=total_events,
        broken_chain=not is_valid,
        invalid_event_id=invalid_id,
        last_verified_event_id=last_verified,
        verification_timestamp=datetime.now(timezone.utc),
    )
