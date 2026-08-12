import pytest
from pydantic import ValidationError
from backend.schemas.policy import PolicyCreateRequest, RiskCalculationRequest

def test_valid_policy_request():
    req = PolicyCreateRequest(
        worker_id="worker_abc",
        latitude=12.9716,
        longitude=77.5946,
        coverage_hours=8,
        coverage_type="combined",
        vehicle_type="motorbike",
    )
    assert req.worker_id == "worker_abc"

def test_invalid_latitude_too_high():
    with pytest.raises(ValidationError):
        PolicyCreateRequest(
            worker_id="worker_abc",
            latitude=999,  # invalid
            longitude=77.5946,
            coverage_hours=8,
            coverage_type="combined",
            vehicle_type="motorbike",
        )

def test_invalid_coverage_hours_zero():
    with pytest.raises(ValidationError):
        PolicyCreateRequest(
            worker_id="worker_abc",
            latitude=12.9716,
            longitude=77.5946,
            coverage_hours=0,  # must be >= 1
            coverage_type="combined",
            vehicle_type="motorbike",
        )

def test_blank_worker_id():
    with pytest.raises(ValidationError):
        PolicyCreateRequest(
            worker_id="   ",  # blank after strip
            latitude=12.9716,
            longitude=77.5946,
            coverage_hours=4,
            coverage_type="rain",
            vehicle_type="bicycle",
        )

def test_invalid_vehicle_type():
    with pytest.raises(ValidationError):
        PolicyCreateRequest(
            worker_id="worker_abc",
            latitude=12.9716,
            longitude=77.5946,
            coverage_hours=4,
            coverage_type="combined",
            vehicle_type="hoverboard",  # not in enum
        )