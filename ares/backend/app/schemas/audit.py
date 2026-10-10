"""Audit Log Schemas."""
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: str
    actor_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    timestamp: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    metadata_json: Dict[str, Any]
    previous_event_hash: Optional[str]
    event_hash: str

    class Config:
        from_attributes = True


class AuditVerificationResponse(BaseModel):
    valid: bool
    total_events: int
    broken_chain: bool
    invalid_event_id: Optional[str] = None
    last_verified_event_id: Optional[str] = None
    verification_timestamp: datetime
