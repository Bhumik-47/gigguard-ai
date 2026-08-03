# tests/test_auth.py
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_protected_route_without_token_returns_401():
    resp = client.get("/calculate")
    assert resp.status_code == 401

def test_protected_route_with_invalid_token_returns_401():
    resp = client.get(
        "/calculate",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 401

@patch("backend.middleware.auth.auth.verify_id_token")
def test_protected_route_with_valid_token(mock_verify):
    mock_verify.return_value = {"uid": "test-user-123", "email": "test@example.com"}
    resp = client.get(
        "/calculate",
        headers={"Authorization": "Bearer valid-mock-token"},
    )
    # Should not be 401
    assert resp.status_code != 401

def test_root_endpoint_is_public():
    resp = client.get("/")
    assert resp.status_code == 200

def test_monitoring_health_is_public():
    resp = client.get("/api/monitoring/health")
    assert resp.status_code == 200
