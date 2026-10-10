"""Case Service: Core business logic for Case lifecycle management."""
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ConflictException
from app.models.case import Case
from app.schemas.case import CaseCreateRequest
from app.services.audit_service import AuditService


class CaseService:
    @staticmethod
    def generate_case_number(db: Session) -> str:
        year = datetime.now(timezone.utc).year
        count = db.query(Case).filter(Case.case_number.like(f"CASE-{year}-%")).count() + 1
        return f"CASE-{year}-{count:06d}"

    @classmethod
    def create_case(cls, db: Session, data: CaseCreateRequest, creator_id: str) -> Case:
        # Check if case_number explicitly provided or generate
        case_number = getattr(data, "case_number", None) or cls.generate_case_number(db)
        
        # Ensure uniqueness of case_number
        existing = db.query(Case).filter(Case.case_number == case_number).first()
        if existing:
            raise ConflictException(f"Case with number '{case_number}' already exists.")

        priority = getattr(data, "priority", None)
        priority_val = priority.value if hasattr(priority, "value") else (priority or "MEDIUM")

        case = Case(
            case_number=case_number,
            title=data.title,
            description=data.description,
            created_by=creator_id,
            priority=priority_val,
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        AuditService.record_event(
            db=db,
            action="CASE_CREATED",
            resource_type="CASE",
            resource_id=case.id,
            actor_id=creator_id,
            metadata={"case_number": case.case_number, "title": case.title},
        )
        return case

    @classmethod
    def get_case(cls, db: Session, case_id: str) -> Case:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ResourceNotFoundException(f"Case '{case_id}' not found.")
        return case

    @classmethod
    def list_cases(cls, db: Session, skip: int = 0, limit: int = 50) -> List[Case]:
        return db.query(Case).order_by(Case.created_at.desc()).offset(skip).limit(limit).all()
