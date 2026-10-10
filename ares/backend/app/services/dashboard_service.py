"""Dashboard aggregation service."""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import AssessmentStatus, DeviceAuthorizationStatus, FindingSeverity, FindingStatus
from app.models.assessment import Assessment
from app.models.audit_log import AuditLog
from app.models.ble_device import BleDevice
from app.models.device import Device
from app.models.esp32_device import ESP32Device
from app.models.finding import Finding
from app.models.wifi_network import WifiNetwork
from app.schemas.dashboard import DashboardSummaryResponse


class DashboardService:
    @staticmethod
    def get_summary(db: Session) -> DashboardSummaryResponse:
        connected_esp32 = db.query(ESP32Device).count()
        authorized_devices = db.query(Device).filter(Device.authorization_status == DeviceAuthorizationStatus.ACTIVE.value).count()
        active_assessments = db.query(Assessment).filter(Assessment.status == AssessmentStatus.RUNNING.value).count()

        open_findings = db.query(Finding).filter(Finding.status == FindingStatus.OPEN.value).count()
        critical_findings = db.query(Finding).filter(
            Finding.status == FindingStatus.OPEN.value,
            Finding.severity == FindingSeverity.CRITICAL.value,
        ).count()

        wifi_devices = db.query(WifiNetwork).count()
        ble_devices = db.query(BleDevice).count()

        recent_logs = (
            db.query(AuditLog)
            .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
            .limit(10)
            .all()
        )
        recent_events = [
            {
                "id": l.id,
                "action": l.action,
                "resource_type": l.resource_type,
                "resource_id": l.resource_id,
                "timestamp": l.timestamp.isoformat(),
            }
            for l in recent_logs
        ]

        return DashboardSummaryResponse(
            connected_esp32=connected_esp32,
            authorized_devices=authorized_devices,
            active_assessments=active_assessments,
            open_findings=open_findings,
            critical_findings=critical_findings,
            wifi_devices=wifi_devices,
            ble_devices=ble_devices,
            recent_events=recent_events,
            system_health="HEALTHY",
        )
