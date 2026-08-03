# backend/tests/test_auth.py
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_protected_route_without_token_returns_401():
    resp = client.post("/api/policy/create", json={})
    assert resp.status_code in (401, 403)

def test_protected_route_with_invalid_token_returns_401():
    resp = client.post(
        "/api/policy/create",
        headers={"Authorization": "Bearer fake-token"},
        json={}
    )
    assert resp.status_code == 401

@patch("middleware.auth.auth.verify_id_token")
def test_protected_route_with_valid_token(mock_verify):
    mock_verify.return_value = {"uid": "test-user-123", "email": "test@example.com"}
    resp = client.post(
        "/api/policy/create",
        headers={"Authorization": "Bearer valid-mock-token"},
        json={"plan": "basic"}
    )
    # Should not be 401
    assert resp.status_code != 401

def test_health_endpoint_is_public():
    resp = client.get("/api/health")
    assert resp.status_code == 200

def test_environment_endpoint_is_public():
    resp = client.get("/api/environment?lat=19.076&lon=72.877")
    # Will hit real API or fail gracefully, but not 401
    assert resp.status_code != 401