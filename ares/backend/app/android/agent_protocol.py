"""ARES-MOBILE/1.0 Protocol and Data Ingestion Service."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.android_device import AndroidDevice
from app.models.application import Application, ApplicationPermission
from app.models.device import Device
from app.schemas.android import AndroidDeviceSyncRequest
from app.services.audit_service import AuditService


class AndroidAgentProtocol:
    PROTOCOL_VERSION = "ARES-MOBILE/1.0"

    @classmethod
    def create_command(cls, command_type: str, request_id: str, device_id: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "protocol": cls.PROTOCOL_VERSION,
            "request_id": request_id,
            "device_id": device_id,
            "type": command_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload or {},
        }

    @staticmethod
    def sync_device_inventory(db: Session, device_id: str, sync_data: AndroidDeviceSyncRequest, actor_id: Optional[str] = None) -> AndroidDevice:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise ResourceNotFoundException("Target device not found.")

        now = datetime.now(timezone.utc)
        android_record = db.query(AndroidDevice).filter(AndroidDevice.device_id == device_id).first()
        if not android_record:
            android_record = AndroidDevice(
                device_id=device.id,
                android_version=sync_data.android_version,
                sdk_version=sync_data.sdk_version,
                manufacturer=sync_data.manufacturer,
                model=sync_data.model,
                security_patch=sync_data.security_patch,
                build_fingerprint_hash=sync_data.build_fingerprint_hash,
                encryption_status=sync_data.encryption_status,
                developer_options_status=sync_data.developer_options_status,
                usb_debugging_status=sync_data.usb_debugging_status,
                vpn_status=sync_data.vpn_status,
                network_security_indicators=sync_data.network_security_indicators,
                unexposed_properties=sync_data.unexposed_properties,
                last_sync=now,
            )
            db.add(android_record)
        else:
            android_record.android_version = sync_data.android_version
            android_record.sdk_version = sync_data.sdk_version
            android_record.security_patch = sync_data.security_patch
            android_record.encryption_status = sync_data.encryption_status
            android_record.developer_options_status = sync_data.developer_options_status
            android_record.usb_debugging_status = sync_data.usb_debugging_status
            android_record.vpn_status = sync_data.vpn_status
            android_record.network_security_indicators = sync_data.network_security_indicators
            android_record.unexposed_properties = sync_data.unexposed_properties
            android_record.last_sync = now

        device.platform_version = f"Android {sync_data.android_version} (API {sync_data.sdk_version})"
        device.security_patch_level = sync_data.security_patch
        device.last_seen_at = now

        # Ingest applications if provided in scope
        if sync_data.applications:
            # Delete older applications for clean refresh
            db.query(Application).filter(Application.device_id == device_id).delete()
            for app_in in sync_data.applications:
                app_obj = Application(
                    device_id=device.id,
                    package_name=app_in.package_name,
                    app_name=app_in.app_name,
                    version_name=app_in.version_name,
                    version_code=app_in.version_code,
                    target_sdk=app_in.target_sdk,
                    min_sdk=app_in.min_sdk,
                    debuggable=app_in.debuggable,
                    system_app=app_in.system_app,
                    created_at=now,
                )
                db.add(app_obj)
                db.flush()

                for perm_in in app_in.permissions:
                    # Deterministic assessment tag
                    is_sensitive = perm_in.protection_level == "dangerous" or any(
                        s in perm_in.permission_name.lower()
                        for s in ("camera", "record_audio", "location", "sms", "contacts", "read_phone_state")
                    )
                    assessment_tag = "REVIEW_REQUIRED" if is_sensitive else "STANDARD"
                    p_obj = ApplicationPermission(
                        application_id=app_obj.id,
                        permission_name=perm_in.permission_name,
                        permission_group=perm_in.permission_group,
                        protection_level=perm_in.protection_level,
                        granted=perm_in.granted,
                        assessment_result=assessment_tag,
                        created_at=now,
                    )
                    db.add(p_obj)

        db.commit()
        db.refresh(android_record)

        AuditService.record_event(
            db=db,
            action="ANDROID_INVENTORY_SYNCED",
            resource_type="DEVICE",
            resource_id=device.id,
            actor_id=actor_id,
            metadata={
                "apps_count": len(sync_data.applications),
                "usb_debugging": sync_data.usb_debugging_status,
                "patch": sync_data.security_patch,
            },
        )
        return android_record
