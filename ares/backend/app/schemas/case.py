"""Case Schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.core.constants import CasePriority, CaseStatus


class CaseCreateRequest(BaseModel):
    case_number: Optional[str] = None
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    priority: CasePriority = CasePriority.MEDIUM


class CaseUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CaseStatus] = None
    priority: Optional[CasePriority] = None


class CaseResponse(BaseModel):
    id: str
    case_number: str
    title: str
    description: Optional[str]
    created_by: str
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]

    class Config:
        from_attributes = True
