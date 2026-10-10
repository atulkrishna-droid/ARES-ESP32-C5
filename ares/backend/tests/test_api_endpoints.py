"""Integration tests for Core REST API Endpoints."""
import pytest


def test_health_endpoints(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "HEALTHY"

    res_ready = client.get("/api/v1/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["ready"] is True

    res_live = client.get("/api/v1/live")
    assert res_live.status_code == 200
    assert res_live.json()["live"] is True


def test_dashboard_summary(client, admin_headers):
    res = client.get("/api/v1/dashboard/summary", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert "connected_esp32" in data
    assert "authorized_devices" in data
    assert "active_assessments" in data
    assert "open_findings" in data
    assert data["system_health"] == "HEALTHY"


def test_case_creation_and_listing(client, admin_headers):
    payload = {
        "title": "API Benchmark Assessment Case",
        "description": "Validation of endpoint response contracts.",
        "priority": "HIGH",
    }
    res = client.post("/api/v1/cases", json=payload, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == payload["title"]
    assert data["case_number"].startswith("CASE-")

    # List cases
    res_list = client.get("/api/v1/cases", headers=admin_headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1


def test_audit_verify_endpoint(client, admin_headers):
    res = client.get("/api/v1/audit/verify", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["broken_chain"] is False


def test_lab_scenarios_endpoint(client, admin_headers):
    res = client.get("/api/v1/lab/scenarios", headers=admin_headers)
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) >= 3
    assert any(s["scenario_id"] == "LAB-SCENARIO-001" for s in scenarios)
