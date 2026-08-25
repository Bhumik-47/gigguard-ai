from pydantic import BaseModel, Field, validator
from typing import Literal, Optional

class PolicyCreateRequest(BaseModel):
    worker_id: str = Field(..., min_length=1, description="Unique worker identifier")
    latitude: float = Field(..., ge=-90, le=90, description="Worker's current latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Worker's current longitude")
    coverage_hours: int = Field(..., ge=1, le=12, description="Shift duration in hours (1–12)")
    coverage_type: Literal["heat", "rain", "aqi", "combined"] = "combined"
    vehicle_type: Literal["bicycle", "motorbike", "car", "walking"]

    @validator("worker_id")
    def worker_id_not_empty(cls, v):
        if not v.strip():
            raise ValueError("worker_id cannot be blank")
        return v

class PolicyCreateResponse(BaseModel):
    policy_id: str
    premium_amount_inr: float
    coverage_start: str  # ISO 8601
    coverage_end: str
    risk_score: float
    status: Literal["active", "pending", "failed"]

class RiskCalculationRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    city: Optional[str] = Field(None, min_length=1, max_length=100)

class RiskCalculationResponse(BaseModel):
    risk_score: float = Field(..., ge=0, le=1)
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    rainfall_mm_per_hr: float
    wind_speed_kmh: float
    temperature_celsius: float
    payout_percentage: float