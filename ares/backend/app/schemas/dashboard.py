"""Dashboard Summary Schema."""
from typing import Any, Dict, List
from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    connected_esp32: int
    authorized_devices: int
    active_assessments: int
    open_findings: int
    critical_findings: int
    wifi_devices: int
    ble_devices: int
    recent_events: List[Dict[str, Any]]
    system_health: str = "HEALTHY"
