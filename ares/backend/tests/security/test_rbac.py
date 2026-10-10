"""Security Audit Tests: Role-Based Access Control (RBAC) (Section 6)."""
import pytest
from app.core.constants import RoleType
from app.core.exceptions import PermissionDeniedException, AuthorizationException
from app.core.security import create_access_token


def test_viewer_cannot_start_assessment(client, seeded_users, auth_headers):
    """Verify that VIEWER role is strictly forbidden from starting assessments."""
    viewer_headers = auth_headers["viewer"]
    
    # Attempt to start assessment
    response = client.post(
        "/api/v1/assessments/test-assessment-id-123/start",
        headers=viewer_headers,
    )
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_viewer_cannot_authorize_devices(client, auth_headers):
    """Verify that VIEWER role cannot authorize devices."""
    viewer_headers = auth_headers["viewer"]
    payload = {
        "case_id": "test-case-id",
        "authorization_method": "OPERATOR_ASSERTED",
        "allowed_operations": ["*"],
    }
    response = client.post(
        "/api/v1/devices/dev-123/authorize",
        json=payload,
        headers=viewer_headers,
    )
    assert response.status_code == 403


def test_viewer_cannot_create_case(client, auth_headers):
    """Verify that VIEWER role cannot create cases."""
    viewer_headers = auth_headers["viewer"]
    payload = {
        "title": "Viewer Case Attempt",
        "description": "Unauthorized attempt",
    }
    response = client.post(
        "/api/v1/cases",
        json=payload,
        headers=viewer_headers,
    )
    assert response.status_code == 403


def test_lab_user_permissions_restricted(client, auth_headers):
    """Verify LAB_USER can access scenarios but cannot modify system configs."""
    lab_headers = auth_headers["lab_user"]
    # Lab user can list scenarios
    resp = client.get("/api/v1/lab/scenarios", headers=lab_headers)
    assert resp.status_code == 200

    # Lab user cannot trigger device authorization without proper permissions
    auth_resp = client.post(
        "/api/v1/devices/prod-dev-1/authorize",
        json={"case_id": "prod-case", "allowed_operations": ["*"]},
        headers=lab_headers,
    )
    assert auth_resp.status_code == 403


def test_analyst_can_create_cases_and_assessments(client, auth_headers):
    """Verify ANALYST can create operational cases."""
    analyst_headers = auth_headers["analyst"]
    case_resp = client.post(
        "/api/v1/cases",
        json={"title": "Analyst Field Assessment", "description": "Field investigation"},
        headers=analyst_headers,
    )
    assert case_resp.status_code == 201
    assert "CASE-" in case_resp.json()["case_number"]


def test_admin_has_full_administrative_access(client, auth_headers):
    """Verify ADMIN role has full authority across protected endpoints."""
    admin_headers = auth_headers["admin"]
    dash_resp = client.get("/api/v1/dashboard/summary", headers=admin_headers)
    assert dash_resp.status_code == 200
    
    audit_resp = client.get("/api/v1/audit/verify", headers=admin_headers)
    assert audit_resp.status_code == 200
