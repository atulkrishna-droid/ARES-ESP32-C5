"""Firmware compatibility validation service."""
from typing import Tuple
from sqlalchemy.orm import Session

from app.core.exceptions import HardwareIncompatibleException, ResourceNotFoundException
from app.models.firmware import Firmware, FirmwareCompatibility
from app.models.hardware_profile import HardwareProfile


class FirmwareService:
    @staticmethod
    def validate_compatibility(
        db: Session, firmware_id: str, hardware_profile_id: str
    ) -> Tuple[bool, str]:
        firmware = db.query(Firmware).filter(Firmware.id == firmware_id).first()
        if not firmware:
            raise ResourceNotFoundException("Firmware not found.")

        profile = db.query(HardwareProfile).filter(HardwareProfile.id == hardware_profile_id).first()
        if not profile:
            raise ResourceNotFoundException("Hardware Profile not found.")

        # 1. Chip Architecture Validation
        if firmware.chip != profile.chip:
            raise HardwareIncompatibleException(
                f"Chip mismatch: Firmware targets '{firmware.chip}', but hardware is '{profile.chip}'."
            )

        # 2. Board Target Validation (e.g., prevent Marauder v8 vs ESP32-C5-DevKitC-1 cross-flashing)
        if firmware.board_target != profile.board_name:
            raise HardwareIncompatibleException(
                f"Board target mismatch: Firmware targets '{firmware.board_target}', but hardware is '{profile.board_name}'. "
                "Cross-flashing distinct board targets is prohibited."
            )

        # 3. Check registered compatibility matrix
        compat = (
            db.query(FirmwareCompatibility)
            .filter(
                FirmwareCompatibility.firmware_id == firmware.id,
                FirmwareCompatibility.hardware_profile_id == profile.id,
            )
            .first()
        )

        if compat:
            if compat.flash_required != profile.flash_size:
                raise HardwareIncompatibleException(
                    f"Flash mismatch: Firmware requires {compat.flash_required}, hardware has {profile.flash_size}."
                )
            if compat.psram_required != profile.psram_size:
                raise HardwareIncompatibleException(
                    f"PSRAM mismatch: Firmware requires {compat.psram_required}, hardware has {profile.psram_size}."
                )

        return True, "Compatible"
