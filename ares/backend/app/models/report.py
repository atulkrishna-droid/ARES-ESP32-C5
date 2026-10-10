"""Security Assessment Report model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    generated_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    format = Column(String(20), default="JSON", nullable=False)  # JSON, HTML
    content_json = Column(JSON, default=dict, nullable=False)
    content_html = Column(Text, nullable=True)
    sha256_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    case = relationship("Case")
    generator = relationship("User", foreign_keys=[generated_by])

    @property
    def total_findings(self) -> int:
        if self.content_json and "findings_summary" in self.content_json:
            return self.content_json["findings_summary"].get("total", 0)
        return 0

    @property
    def compliance_score(self) -> float:
        if not self.content_json or "findings_summary" not in self.content_json:
            return 100.0
        tot = self.total_findings
        if tot == 0:
            return 100.0
        summary = self.content_json.get("findings_summary", {})
        deductions = (
            summary.get("critical", 0) * 25
            + summary.get("high", 0) * 15
            + summary.get("medium", 0) * 10
            + summary.get("low", 0) * 5
        )
        return max(0.0, float(100 - deductions))
