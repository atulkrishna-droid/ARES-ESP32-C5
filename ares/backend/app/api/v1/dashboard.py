"""Dashboard Summary Endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import require_permission
from app.core.database import get_db
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse, dependencies=[Depends(require_permission("device.read"))])
def get_dashboard_summary(db: Session = Depends(get_db)):
    return DashboardService.get_summary(db)
