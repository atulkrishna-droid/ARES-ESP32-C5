"""Assessment and Finding Schemas."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.constants import AssessmentStatus, AssessmentType, FindingSeverity, FindingStatus


class AssessmentCreateRequest(BaseModel):
    case_id: str
    target_device_id: str
    assessment_type: AssessmentType = AssessmentType.DEVICE_SECURITY
    scope: Optional[Dict[str, Any]] = None
    scope_json: Optional[Dict[str, Any]] = None

    def get_effective_scope(self) -> Dict[str, Any]:
        return self.scope_json or self.scope or {
            "device_ids": [],
            "network_ids": [],
            "allowed_operations": ["DEVICE_INVENTORY", "SECURITY_POSTURE"],
            "expires_at": None,
        }


class AssessmentAuthorizeRequest(BaseModel):
    confirmed: bool = True
    authorization_notes: Optional[str] = "Authorized assessment within approved scope."


class FindingResponse(BaseModel):
    id: str
    assessment_id: str
    rule_id: str
    device_id: str
    application_id: Optional[str] = None
    severity: str
    title: str
    description: str
    evidence_json: Dict[str, Any] = {}
    recommendation: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FindingUpdateRequest(BaseModel):
    status: FindingStatus
    resolution_notes: Optional[str] = None


class AssessmentResponse(BaseModel):
    id: str
    case_id: str
    target_device_id: str
    assessment_type: str
    status: str
    scope_json: Dict[str, Any]
    created_by: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    findings_count: Optional[int] = 0

    class Config:
        from_attributes = True
