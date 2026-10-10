"""API v1 Central Router Aggregation."""
from fastapi import APIRouter

from app.api.v1.android import router as android_router
from app.api.v1.assessments import router as assessments_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.cases import router as cases_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.devices import router as devices_router
from app.api.v1.esp32 import router as esp32_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.findings import router as findings_router
from app.api.v1.health import router as health_router
from app.api.v1.lab import router as lab_router
from app.api.v1.reports import router as reports_router
from app.api.v1.users import router as users_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(cases_router)
api_v1_router.include_router(devices_router)
api_v1_router.include_router(esp32_router)
api_v1_router.include_router(android_router)
api_v1_router.include_router(assessments_router)
api_v1_router.include_router(findings_router)
api_v1_router.include_router(evidence_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(lab_router)
api_v1_router.include_router(dashboard_router)
