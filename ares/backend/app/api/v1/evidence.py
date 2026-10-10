"""Forensics Evidence and Custody Endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_permission
from app.core.database import get_db
from app.models.evidence import ChainOfCustodyEvent, Evidence
from app.models.user import User
from app.schemas.evidence import ChainOfCustodyResponse, EvidenceCreateRequest, EvidenceResponse
from app.services.evidence_service import EvidenceService

router = APIRouter(prefix="/evidence", tags=["Evidence"])


@router.post("", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("evidence.create"))])
def create_evidence(
    request: EvidenceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evidence = EvidenceService.create_evidence(db, request, actor_id=current_user.id)
    return evidence


@router.get("", response_model=List[EvidenceResponse], dependencies=[Depends(require_permission("evidence.read"))])
def list_evidence(
    case_id: Optional[str] = None,
    assessment_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(Evidence)
    if case_id:
        query = query.filter(Evidence.case_id == case_id)
    if assessment_id:
        query = query.filter(Evidence.assessment_id == assessment_id)
    return query.order_by(Evidence.collected_at.desc()).offset(skip).limit(limit).all()


@router.get("/{evidence_id}", response_model=EvidenceResponse, dependencies=[Depends(require_permission("evidence.read"))])
def get_evidence(evidence_id: str, db: Session = Depends(get_db)):
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found.")
    return evidence


@router.get("/{evidence_id}/hash", dependencies=[Depends(require_permission("evidence.read"))])
def get_evidence_hash(evidence_id: str, db: Session = Depends(get_db)):
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found.")
    return {
        "evidence_id": evidence.id,
        "name": evidence.name,
        "sha256": evidence.sha256,
        "sha512": evidence.sha512,
        "size_bytes": evidence.size_bytes,
        "collected_at": evidence.collected_at.isoformat(),
    }


@router.get("/{evidence_id}/chain", response_model=List[ChainOfCustodyResponse], dependencies=[Depends(require_permission("evidence.read"))])
def get_evidence_chain_of_custody(evidence_id: str, db: Session = Depends(get_db)):
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found.")
    return (
        db.query(ChainOfCustodyEvent)
        .filter(ChainOfCustodyEvent.evidence_id == evidence_id)
        .order_by(ChainOfCustodyEvent.timestamp.asc())
        .all()
    )
