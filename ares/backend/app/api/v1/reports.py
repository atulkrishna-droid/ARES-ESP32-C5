"""Report Generation Endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_permission
from app.core.database import get_db
from app.models.report import Report
from app.models.user import User
from app.schemas.report import ReportCreateRequest, ReportResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("report.generate"))])
def generate_report(
    request: ReportCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ReportService.generate_report(
        db, case_id=request.case_id, actor_id=current_user.id, format_type=request.format, title=request.title
    )


@router.get("", response_model=List[ReportResponse], dependencies=[Depends(require_permission("report.read"))])
def list_reports(case_id: Optional[str] = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(Report)
    if case_id:
        query = query.filter(Report.case_id == case_id)
    return query.order_by(Report.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{report_id}", response_model=ReportResponse, dependencies=[Depends(require_permission("report.read"))])
def get_report(report_id: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report


@router.get("/{report_id}/html", dependencies=[Depends(require_permission("report.read"))])
def get_report_html(report_id: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or not report.content_html:
        raise HTTPException(status_code=404, detail="Report HTML format not available.")
    return Response(content=report.content_html, media_type="text/html")
