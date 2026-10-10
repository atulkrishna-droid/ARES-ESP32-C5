"""ESP32 Device Controller and Scan Result Ingestor."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.exceptions import DeviceNotAuthorizedException, ResourceNotFoundException, ScopeViolationException
from app.core.security import sha256_hash
from app.models.assessment import Assessment
from app.models.ble_device import BleDevice
from app.models.device import Device
from app.models.esp32_device import ESP32Device
from app.models.wifi_network import WifiNetwork
from app.schemas.bluetooth import BleScanResultIngest
from app.schemas.esp32 import ESP32TelemetryRequest
from app.schemas.wifi import WifiScanResultIngest
from app.services.audit_service import AuditService


class ESP32DeviceManager:
    @staticmethod
    def update_telemetry(db: Session, device_id: str, telemetry: ESP32TelemetryRequest) -> ESP32Device:
        esp = db.query(ESP32Device).filter(ESP32Device.device_id == device_id).first()
        if not esp:
            raise ResourceNotFoundException("ESP32 Device not found.")

        now = datetime.now(timezone.utc)
        esp.last_heartbeat = now
        esp.latest_telemetry = telemetry.model_dump()
        esp.status = "ONLINE"

        # Update parent device last seen
        if esp.device:
            esp.device.last_seen_at = now

        db.commit()
        db.refresh(esp)
        return esp

    @staticmethod
    def ingest_wifi_scan_results(
        db: Session, assessment_id: str, results: List[WifiScanResultIngest], actor_id: Optional[str] = None
    ) -> List[WifiNetwork]:
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise ResourceNotFoundException("Assessment not found.")

        now = datetime.now(timezone.utc)
        records = []
        for r in results:
            bssid_hash = sha256_hash(r.bssid.lower().encode("utf-8"))
            net = WifiNetwork(
                assessment_id=assessment.id,
                ssid=r.ssid,
                bssid_hash=bssid_hash,
                channel=r.channel,
                frequency=r.frequency,
                band=r.band,
                rssi=r.rssi,
                security_type=r.security_type,
                vendor=r.vendor,
                first_seen=now,
                last_seen=now,
            )
            db.add(net)
            records.append(net)

        db.commit()
        AuditService.record_event(
            db=db,
            action="WIFI_SCAN_INGESTED",
            resource_type="ASSESSMENT",
            resource_id=assessment.id,
            actor_id=actor_id,
            metadata={"count": len(records), "band_types": list(set(r.band for r in results))},
        )
        return records

    @staticmethod
    def ingest_ble_scan_results(
        db: Session, assessment_id: str, results: List[BleScanResultIngest], actor_id: Optional[str] = None
    ) -> List[BleDevice]:
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            raise ResourceNotFoundException("Assessment not found.")

        now = datetime.now(timezone.utc)
        records = []
        for r in results:
            addr_hash = sha256_hash(r.device_address.lower().encode("utf-8"))
            data_hash = sha256_hash(r.manufacturer_data_hex.encode("utf-8")) if r.manufacturer_data_hex else None
            ble = BleDevice(
                assessment_id=assessment.id,
                device_address_hash=addr_hash,
                name=r.name,
                rssi=r.rssi,
                manufacturer_id=r.manufacturer_id,
                manufacturer_data_hash=data_hash,
                service_uuids=r.service_uuids,
                first_seen=now,
                last_seen=now,
            )
            db.add(ble)
            records.append(ble)

        db.commit()
        AuditService.record_event(
            db=db,
            action="BLE_SCAN_INGESTED",
            resource_type="ASSESSMENT",
            resource_id=assessment.id,
            actor_id=actor_id,
            metadata={"count": len(records)},
        )
        return records
