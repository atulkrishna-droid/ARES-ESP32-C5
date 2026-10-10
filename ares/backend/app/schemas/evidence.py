"""Forensics Evidence and Custody Schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.core.constants import ChainOfCustodyEventType, EvidenceType


class EvidenceCreateRequest(BaseModel):
    case_id: str
    assessment_id: Optional[str] = None
    device_id: Optional[str] = None
    type: EvidenceType = EvidenceType.DEVICE_METADATA
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    source: str = "ESP32_C5"
    raw_content: str = Field(..., description="Base64 or utf-8 encoded content string for evidence file")


class ChainOfCustodyResponse(BaseModel):
    id: str
    evidence_id: str
    actor_id: str
    event_type: str
    timestamp: datetime
    description: str
    previous_hash: Optional[str]
    event_hash: str

    class Config:
        from_attributes = True


class EvidenceResponse(BaseModel):
    id: str
    case_id: str
    assessment_id: Optional[str]
    device_id: Optional[str]
    type: str
    name: str
    description: Optional[str]
    source: str
    path_reference: str
    sha256: str
    sha512: Optional[str]
    size_bytes: int
    collected_at: datetime
    collected_by: str
    created_at: datetime

    class Config:
        from_attributes = True
