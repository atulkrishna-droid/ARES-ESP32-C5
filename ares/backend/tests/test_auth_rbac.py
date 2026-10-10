"""Unit and integration tests for Authentication and RBAC."""
import pytest
from app.core.security import verify_password
from app.services.auth_service import AuthService
from app.schemas.auth import UserRegisterRequest


def test_password_hashing():
    pwd = "SecureP@ssw0rd2026!"
    hashed = AuthService.register  # checking security function directly
    from app.core.security import hash_password
    h = hash_password(pwd)
    assert h.startswith("pbkdf2_sha256$600000$")
    assert verify_password(pwd, h) is True
    assert verify_password("WrongPassword!", h) is False


def test_user_registration_and_login(db_session):
    req = UserRegisterRequest(
        email="newuser@ares.internal",
        username="newanalyst",
        password="TestPassword123!",
        display_name="New Analyst",
        role="ANALYST",
    )
    user = AuthService.register(db_session, req)
    assert user.id is not None
    assert user.username == "newanalyst"

    login_res = AuthService.login(db_session, "newanalyst", "TestPassword123!")
    assert login_res.access_token is not None
    assert login_res.refresh_token is not None
    assert login_res.user_id == user.id

    # Test token refresh
    refresh_res = AuthService.refresh(db_session, login_res.refresh_token)
    assert refresh_res.access_token is not None


def test_rbac_endpoint_access(client, admin_headers, viewer_headers):
    # Admin can access /api/v1/users (has '*')
    res_admin = client.get("/api/v1/users", headers=admin_headers)
    assert res_admin.status_code == 200

    # Viewer has no user.read permission, must be rejected 403
    res_viewer = client.get("/api/v1/users", headers=viewer_headers)
    assert res_viewer.status_code == 403

    # Unauthenticated request must be rejected 401
    res_unauth = client.get("/api/v1/users")
    assert res_unauth.status_code == 401
