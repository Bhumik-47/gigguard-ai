from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from backend.main import app

client = TestClient(app)

def test_claim_history_returns_claims():
    res = client.get("/api/claims/history/worker_001")
    assert res.status_code == 200
    data = res.json()
    assert "claims" in data
    assert "total_lifetime_payout_inr" in data
    assert data["worker_id"] == "worker_001"

def test_claim_history_blank_worker_id():
    res = client.get("/api/claims/history/%20")  # URL-encoded space
    assert res.status_code in [400, 422]

def test_claim_history_limit_respected():
    res = client.get("/api/claims/history/worker_001?limit=2")
    assert res.status_code == 200
    assert res.json()["total"] <= 2