# backend/schemas/environmental.py
from pydantic import BaseModel, Field, field_validator

class EnvironmentalTriggerPayload(BaseModel):
    policy_id: str
    aqi: float = Field(..., ge=0, le=500, description="Air Quality Index (0–500)")
    temperature_celsius: float = Field(..., ge=-50, le=60, description="Temperature in Celsius")
    rainfall_mm_per_hour: float = Field(..., ge=0, description="Rainfall in mm/hr")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

    @field_validator('policy_id')
    @classmethod
    def policy_id_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('policy_id cannot be empty or whitespace')
        return v.strip()


class RiskCalculationPayload(BaseModel):
    rainfall_mm: float = Field(..., ge=0, le=500)
    wind_speed_kmh: float = Field(..., ge=0, le=400)
    aqi: float = Field(..., ge=0, le=500)