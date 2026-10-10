"""Health Check Endpoints."""
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "UP"
    except Exception as e:
        db_status = f"DOWN: {str(e)}"

    return {
        "status": "HEALTHY" if db_status == "UP" else "DEGRADED",
        "components": {
            "database": db_status,
            "api": "UP",
        },
    }


@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"ready": True}


@router.get("/live")
def liveness_check():
    return {"live": True}
