"""Cryptographic functions, password hashing, and token issuance."""
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 600,000 iterations and 16-byte salt."""
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
    return f"pbkdf2_sha256$600000${salt.hex()}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored PBKDF2-HMAC-SHA256 hash."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_key = bytes.fromhex(parts[3])
        calculated_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(expected_key, calculated_key)
    except Exception:
        return False


_REVOKED_JTIS: set[str] = set()


def revoke_token(token: str) -> None:
    """Revoke a token by recording its JTI or raw token string."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM], options={"verify_exp": False})
        jti = payload.get("jti")
        if jti:
            _REVOKED_JTIS.add(jti)
    except Exception:
        pass
    _REVOKED_JTIS.add(token)


def is_token_revoked(token: str) -> bool:
    """Check if token or its JTI has been revoked."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM], options={"verify_exp": False})
        jti = payload.get("jti")
        if jti and jti in _REVOKED_JTIS:
            return True
    except Exception:
        pass
    return token in _REVOKED_JTIS


def create_access_token(
    subject: str = "",
    roles: Optional[list[str]] = None,
    permissions: Optional[list[str]] = None,
    expires_delta: Optional[timedelta] = None,
    data: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    if isinstance(subject, dict):
        data = subject
        sub = data.get("sub")
    else:
        sub = subject
    r = roles or []
    p = permissions or []
    if data:
        sub = data.get("sub", sub)
        if "role" in data and not r:
            r = [data["role"]]
        if "roles" in data:
            r = data["roles"]

    payload = {
        "sub": sub,
        "roles": r,
        "permissions": p,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT refresh token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": subject,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token signature, expiration, and revocation status."""
    from app.core.exceptions import AuthenticationException
    if is_token_revoked(token):
        raise AuthenticationException("Token has been revoked.")
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AuthenticationException("Token has expired.")
    except jwt.PyJWTError as e:
        raise AuthenticationException(f"Invalid token: {str(e)}")


def sha256_hash(data: Any) -> str:
    """Compute SHA-256 hash of byte sequence or string."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def sha512_hash(data: Any) -> str:
    """Compute SHA-512 hash of byte sequence or string."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha512(data).hexdigest()


def canonical_json_bytes(obj: Any) -> bytes:
    """Serialize dictionary or primitive to canonical JSON with sorted keys and no whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
