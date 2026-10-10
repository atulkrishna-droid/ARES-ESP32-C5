"""Custom exceptions and error structures for ARES Platform."""
from typing import Any, Optional


class AresException(Exception):
    """Base exception for all ARES domain errors."""
    code: str = "ARES_ERROR"
    message: str = "An unexpected error occurred in the ARES platform."
    status_code: int = 400

    def __init__(self, message: Optional[str] = None, details: Optional[Any] = None):
        if message:
            self.message = message
        self.details = details
        super().__init__(self.message)


class AuthenticationFailedException(AresException):
    code = "AUTHENTICATION_FAILED"
    message = "Invalid credentials or expired session token."
    status_code = 401


class PermissionDeniedException(AresException):
    code = "PERMISSION_DENIED"
    message = "You do not have permission to perform this action."
    status_code = 403


class DeviceNotAuthorizedException(AresException):
    code = "DEVICE_NOT_AUTHORIZED"
    message = "The selected device is not authorized for this assessment."
    status_code = 403


class ScopeViolationException(AresException):
    code = "SCOPE_VIOLATION"
    message = "Requested operation violates the approved assessment scope."
    status_code = 403


class ResourceNotFoundException(AresException):
    code = "RESOURCE_NOT_FOUND"
    message = "The requested resource could not be found."
    status_code = 404


class HardwareIncompatibleException(AresException):
    code = "HARDWARE_INCOMPATIBLE"
    message = "Firmware or operation is incompatible with the target hardware profile."
    status_code = 400


class ProtocolViolationException(AresException):
    code = "PROTOCOL_VIOLATION"
    message = "ARES protocol specification violation."
    status_code = 400


class InvalidProtocolMessageException(ProtocolViolationException):
    code = "INVALID_PROTOCOL_MESSAGE"
    message = "Message does not conform to ARES protocol specification."


class UnknownCommandException(ProtocolViolationException):
    code = "COMMAND_REJECTED"
    message = "The requested command is not in the allowed command whitelist."


class DeviceBusyException(AresException):
    code = "DEVICE_BUSY"
    message = "The device is currently locked by another active assessment."
    status_code = 409


class AuditTamperDetectedException(AresException):
    code = "AUDIT_TAMPER_DETECTED"
    message = "Cryptographic integrity check failed. Audit log chain has been broken or modified."
    status_code = 500


# Aliases & Specialized Domain Exceptions
AuthenticationException = AuthenticationFailedException
AuthorizationException = PermissionDeniedException
ConflictException = DeviceBusyException


class ForensicIntegrityException(AresException):
    code = "FORENSIC_INTEGRITY_VIOLATION"
    message = "Forensic hash verification failed. Evidence has been modified or corrupted."
    status_code = 400


class StorageException(AresException):
    code = "STORAGE_ERROR"
    message = "File storage boundary violated or storage failure."
    status_code = 400

