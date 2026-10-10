"""Security Audit Tests: Authentication & Session Security (Section 5)."""
import time
import pytest
from datetime import timedelta
import jwt
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
    hash_password,
)
from app.models.user import User
from app.services.auth_service import AuthService
from app.core.exceptions import AuthenticationException


def test_password_never_exposed_or_plaintext(db_session, seeded_users):
    """Verify that password hash is irreversible and raw password is not stored."""
    admin = seeded_users["admin"]
    assert admin.password_hash != "AdminPass123!"
    assert verify_password("AdminPass123!", admin.password_hash) is True
    assert verify_password("WrongPassword!", admin.password_hash) is False
    assert not hasattr(admin, "password")


def test_jwt_secrets_not_default_empty():
    """Verify JWT secret is configured and not default empty."""
    assert len(settings.JWT_SECRET_KEY) >= 32
    assert settings.JWT_ALGORITHM == "HS256"


def test_expired_access_token_rejected():
    """Verify that tokens expired in the past are rejected with AuthenticationException."""
    token = create_access_token(
        data={"sub": "user-123", "role": "ANALYST"},
        expires_delta=timedelta(seconds=-10),
    )
    with pytest.raises(AuthenticationException):
        decode_token(token)


def test_tampered_token_signature_rejected():
    """Verify that tokens signed with a different key are rejected."""
    tampered_token = jwt.encode(
        {"sub": "user-123", "role": "ADMIN", "exp": int(time.time()) + 3600},
        "wrong-secret-key-attacker-signature-12345",
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationException):
        decode_token(tampered_token)


def test_disabled_user_cannot_authenticate(db_session):
    """Verify that disabled/deactivated users cannot log in."""
    user = User(
        email="disabled.analyst@ares.internal",
        username="disabled_analyst",
        password_hash=hash_password("SecurePassword123!"),
        display_name="Disabled Analyst",
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    with pytest.raises(AuthenticationException) as exc_info:
        AuthService.login(db_session, "disabled.analyst@ares.internal", "SecurePassword123!")
    assert "deactivated" in str(exc_info.value).lower() or "disabled" in str(exc_info.value).lower()


def test_refresh_token_rotation_and_reuse_prevention(db_session, seeded_users):
    """Verify refresh token rotation invalidates old tokens and rejects reuse."""
    analyst = seeded_users["analyst"]
    
    # Login produces access and refresh tokens
    login_result = AuthService.login(db_session, analyst.email, "AnalystPass123!")
    old_refresh_token = login_result.refresh_token

    # Rotate refresh token
    rotated_result = AuthService.refresh_access_token(db_session, old_refresh_token)
    new_refresh_token = rotated_result.refresh_token
    assert new_refresh_token != old_refresh_token

    # Attempt to reuse old refresh token -> Must be rejected!
    with pytest.raises(AuthenticationException) as exc_info:
        AuthService.refresh_access_token(db_session, old_refresh_token)
    assert "revoked" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()


def test_revoked_session_logout(db_session, seeded_users):
    """Verify that logging out revokes the session and prevents token refreshing."""
    lab_user = seeded_users["lab_user"]
    login_result = AuthService.login(db_session, lab_user.email, "LabUserPass123!")
    refresh_token = login_result.refresh_token

    # Logout
    AuthService.logout(db_session, refresh_token)

    # Attempt to refresh with logged-out session token
    with pytest.raises(AuthenticationException):
        AuthService.refresh_access_token(db_session, refresh_token)
