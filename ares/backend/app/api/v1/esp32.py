"""ESP32-C5 Hardware Controller Endpoints."""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, require_permission
from app.core.database import get_db
from app.core.exceptions import DeviceNotAuthorizedException, ResourceNotFoundException
from app.esp32.capability_parser import CapabilityParser
from app.esp32.device_manager import ESP32DeviceManager
from app.esp32.protocol import AresProtocol
from app.esp32.simulator import ESP32Simulator
from app.models.device import Device
from app.models.esp32_device import ESP32Device
from app.models.hardware_profile import HardwareProfile
from app.models.user import User
from app.schemas.bluetooth import BleDeviceResponse, BleScanResultIngest
from app.schemas.esp32 import ESP32PairRequest, ESP32Response, ESP32TelemetryRequest, HardwareProfileResponse
from app.schemas.wifi import WifiNetworkResponse, WifiScanResultIngest

router = APIRouter(prefix="/esp32", tags=["ESP32 Hardware"])


@router.get("", response_model=List[ESP32Response], dependencies=[Depends(require_permission("esp32.read"))])
def list_esp32_devices(db: Session = Depends(get_db)):
    return db.query(ESP32Device).all()


@router.post("/pair", response_model=ESP32Response, dependencies=[Depends(require_permission("esp32.connect"))])
def pair_esp32(request: ESP32PairRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check or create parent device
    device = db.query(Device).filter(Device.device_uuid == request.device_uuid).first()
    if not device:
        device = Device(
            device_uuid=request.device_uuid,
            device_type="ESP32",
            manufacturer="Espressif",
            model=request.board_name,
            platform="ESP_IDF",
            authorization_status="AUTHORIZED",
            operational_status="READY",
        )
        db.add(device)
        db.flush()

    esp = db.query(ESP32Device).filter(ESP32Device.device_id == device.id).first()
    if not esp:
        profile = db.query(HardwareProfile).filter(HardwareProfile.board_name == request.board_name).first()
        esp = ESP32Device(
            device_id=device.id,
            hardware_profile_id=profile.id if profile else None,
            chip=request.chip,
            board_name=request.board_name,
            board_revision=request.board_revision,
            flash_size=request.flash_size,
            psram_size=request.psram_size,
            firmware_version=request.firmware_version,
            protocol_version=request.protocol_version,
            status="READY",
        )
        db.add(esp)
    else:
        esp.status = "READY"
        esp.firmware_version = request.firmware_version

    db.commit()
    db.refresh(esp)
    return esp


@router.get("/{device_id}/capabilities", response_model=Dict[str, Any], dependencies=[Depends(require_permission("esp32.read"))])
def get_capabilities(device_id: str, db: Session = Depends(get_db)):
    esp = db.query(ESP32Device).filter(ESP32Device.device_id == device_id).first()
    if not esp:
        raise HTTPException(status_code=404, detail="ESP32 device not found.")

    raw = {"chip": esp.chip, "board": esp.board_name, "flash": esp.flash_size, "psram": esp.psram_size}
    return CapabilityParser.parse_esp32_c5_devkit(raw)


@router.post("/{device_id}/telemetry", response_model=ESP32Response)
def report_telemetry(device_id: str, telemetry: ESP32TelemetryRequest, db: Session = Depends(get_db)):
    return ESP32DeviceManager.update_telemetry(db, device_id, telemetry)


@router.post("/{device_id}/wifi/scan", response_model=List[WifiNetworkResponse], dependencies=[Depends(require_permission("esp32.scan"))])
def execute_wifi_scan(
    device_id: str,
    assessment_id: str,
    band: str = "ALL",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    esp = db.query(ESP32Device).filter(ESP32Device.device_id == device_id).first()
    if not esp:
        raise HTTPException(status_code=404, detail="ESP32 device not found.")

    if not esp.device or not esp.device.is_authorized():
        raise HTTPException(status_code=403, detail="ESP32 hardware is not in ACTIVE authorization status.")

    from app.models.assessment import Assessment
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found.")

    if assessment.target_device_id != device_id:
        raise HTTPException(status_code=403, detail="Assessment target device does not match the specified ESP32 device.")

    scope = assessment.scope_json or {}
    allowed_ops = scope.get("allowed_operations", [])
    if "*" not in allowed_ops and "WIFI_DISCOVERY" not in allowed_ops:
        raise HTTPException(status_code=403, detail="Operation 'WIFI_DISCOVERY' is not authorized in this assessment scope.")

    # Use simulator to generate realistic scan observations for development
    sim = ESP32Simulator(device_uuid=esp.device.device_uuid)
    scan_msg = sim.simulate_wifi_scan(band=band)
    networks_raw = scan_msg["payload"]["networks"]

    ingest_models = [WifiScanResultIngest(**net) for net in networks_raw]
    records = ESP32DeviceManager.ingest_wifi_scan_results(db, assessment_id, ingest_models, actor_id=current_user.id)
    return records


@router.post("/{device_id}/ble/scan", response_model=List[BleDeviceResponse], dependencies=[Depends(require_permission("esp32.scan"))])
def execute_ble_scan(
    device_id: str,
    assessment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    esp = db.query(ESP32Device).filter(ESP32Device.device_id == device_id).first()
    if not esp:
        raise HTTPException(status_code=404, detail="ESP32 device not found.")

    if not esp.device or not esp.device.is_authorized():
        raise HTTPException(status_code=403, detail="ESP32 hardware is not in ACTIVE authorization status.")

    from app.models.assessment import Assessment
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found.")

    if assessment.target_device_id != device_id:
        raise HTTPException(status_code=403, detail="Assessment target device does not match the specified ESP32 device.")

    scope = assessment.scope_json or {}
    allowed_ops = scope.get("allowed_operations", [])
    if "*" not in allowed_ops and "BLE_DISCOVERY" not in allowed_ops:
        raise HTTPException(status_code=403, detail="Operation 'BLE_DISCOVERY' is not authorized in this assessment scope.")

    sim = ESP32Simulator(device_uuid=esp.device.device_uuid)
    scan_msg = sim.simulate_ble_scan()
    ble_raw = scan_msg["payload"]["devices"]

    ingest_models = [BleScanResultIngest(**b) for b in ble_raw]
    records = ESP32DeviceManager.ingest_ble_scan_results(db, assessment_id, ingest_models, actor_id=current_user.id)
    return records


@router.post("/{device_id}/stop", dependencies=[Depends(require_permission("esp32.connect"))])
def stop_esp32_operation(device_id: str, db: Session = Depends(get_db)):
    esp = db.query(ESP32Device).filter(ESP32Device.device_id == device_id).first()
    if not esp:
        raise HTTPException(status_code=404, detail="ESP32 device not found.")
    esp.status = "READY"
    if esp.device:
        esp.device.operational_status = "READY"
    db.commit()
    return {"message": "ESP32 operation halted. Device is ready."}
