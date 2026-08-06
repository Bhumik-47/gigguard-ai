# backend/tests/test_rate_limiter.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_environmental_payload_valid():
    payload = {
        "policy_id": "POL-001",
        "aqi": 150.0,
        "temperature_celsius": 35.0,
        "rainfall_mm_per_hour": 5.0,
        "latitude": 12.97,
        "longitude": 77.59
    }
    # Validates schema doesn't raise
    from schemas.environmental import EnvironmentalTriggerPayload
    obj = EnvironmentalTriggerPayload(**payload)
    assert obj.policy_id == "POL-001"

def test_environmental_payload_invalid_aqi():
    from pydantic import ValidationError
    from schemas.environmental import EnvironmentalTriggerPayload
    with pytest.raises(ValidationError):
        EnvironmentalTriggerPayload(
            policy_id="POL-001",
            aqi=999,  # exceeds max 500
            temperature_celsius=35.0,
            rainfall_mm_per_hour=5.0,
            latitude=12.97,
            longitude=77.59
        )

def test_empty_policy_id_rejected():
    from pydantic import ValidationError
    from schemas.environmental import EnvironmentalTriggerPayload
    with pytest.raises(ValidationError):
        EnvironmentalTriggerPayload(
            policy_id="   ",
            aqi=100,
            temperature_celsius=30,
            rainfall_mm_per_hour=2,
            latitude=12.97,
            longitude=77.59
        )