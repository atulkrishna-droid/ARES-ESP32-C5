"""Assessment Execution and Evaluation Endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_permission
from app.assessment.engine import AssessmentEngine
from app.core.database import get_db
from app.models.assessment import Assessment
from app.models.case import Case
from app.models.device import Device
from app.models.user import User
from app.schemas.assessment import (
    AssessmentAuthorizeRequest,
    AssessmentCreateRequest,
    AssessmentResponse,
    FindingResponse,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/assessments", tags=["Assessments"])


@router.post("", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("assessment.create"))])
def create_assessment(request: AssessmentCreateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == request.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Target Case not found.")

    device = db.query(Device).filter(Device.id == request.target_device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Target Device not found.")

    assessment = Assessment(
        case_id=case.id,
        target_device_id=device.id,
        assessment_type=request.assessment_type.value,
        status="CREATED",
        scope_json=request.scope,
        created_by=current_user.id,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    AuditService.record_event(
        db=db,
        action="ASSESSMENT_CREATED",
        resource_type="ASSESSMENT",
        resource_id=assessment.id,
        actor_id=current_user.id,
        metadata={"case_id": case.id, "target_device_id": device.id},
    )
    return assessment


@router.get("", response_model=List[AssessmentResponse], dependencies=[Depends(require_permission("assessment.read"))])
def list_assessments(case_id: str = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(Assessment)
    if case_id:
        query = query.filter(Assessment.case_id == case_id)
    return query.offset(skip).limit(limit).all()


@router.get("/{assessment_id}", response_model=AssessmentResponse, dependencies=[Depends(require_permission("assessment.read"))])
def get_assessment(assessment_id: str, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    return assessment


@router.post("/{assessment_id}/start", response_model=AssessmentResponse, dependencies=[Depends(require_permission("assessment.start"))])
def start_assessment(assessment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AssessmentEngine.start_assessment(db, assessment_id, actor_id=current_user.id)


@router.post("/{assessment_id}/evaluate", response_model=List[FindingResponse], dependencies=[Depends(require_permission("assessment.start"))])
def evaluate_assessment(assessment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    findings = AssessmentEngine.run_evaluation(db, assessment_id, actor_id=current_user.id)
    return findings


@router.post("/{assessment_id}/stop", response_model=AssessmentResponse, dependencies=[Depends(require_permission("assessment.stop"))])
def stop_assessment(assessment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AssessmentEngine.stop_assessment(db, assessment_id, actor_id=current_user.id)
