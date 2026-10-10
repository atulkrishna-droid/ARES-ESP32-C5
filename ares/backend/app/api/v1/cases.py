"""Case Management Endpoints."""
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_permission
from app.core.database import get_db
from app.models.case import Case
from app.models.user import User
from app.schemas.case import CaseCreateRequest, CaseResponse, CaseUpdateRequest
from app.services.audit_service import AuditService

router = APIRouter(prefix="/cases", tags=["Cases"])


def generate_case_number(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    count = db.query(Case).filter(Case.case_number.like(f"CASE-{year}-%")).count() + 1
    return f"CASE-{year}-{count:06d}"


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("case.write"))])
def create_case(request: CaseCreateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    case_num = generate_case_number(db)
    case = Case(
        case_number=case_num,
        title=request.title,
        description=request.description,
        created_by=current_user.id,
        priority=request.priority.value,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    AuditService.record_event(
        db=db,
        action="CASE_CREATED",
        resource_type="CASE",
        resource_id=case.id,
        actor_id=current_user.id,
        metadata={"case_number": case.case_number, "title": case.title},
    )
    return case


@router.get("", response_model=List[CaseResponse], dependencies=[Depends(require_permission("case.read"))])
def list_cases(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Case).order_by(Case.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{case_id}", response_model=CaseResponse, dependencies=[Depends(require_permission("case.read"))])
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case


@router.patch("/{case_id}", response_model=CaseResponse, dependencies=[Depends(require_permission("case.write"))])
def update_case(case_id: str, request: CaseUpdateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    if request.title is not None:
        case.title = request.title
    if request.description is not None:
        case.description = request.description
    if request.status is not None:
        case.status = request.status.value
    if request.priority is not None:
        case.priority = request.priority.value

    db.commit()
    db.refresh(case)
    return case
