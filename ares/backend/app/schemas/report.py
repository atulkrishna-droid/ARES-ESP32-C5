"""Report Schemas."""
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ReportCreateRequest(BaseModel):
    case_id: str
    title: Optional[str] = None
    format: str = "JSON"  # JSON, HTML


class ReportResponse(BaseModel):
    id: str
    case_id: str
    title: str
    generated_by: str
    format: str
    sha256_hash: str
    created_at: datetime
    content_json: Dict[str, Any] = {}
    content_html: Optional[str] = None

    class Config:
        from_attributes = True
