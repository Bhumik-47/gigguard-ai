# backend/routes/environment.py
"""
GET /api/environment/status
Returns current environmental conditions vs policy trigger thresholds.
Used by the frontend EnvironmentAlertBanner to poll every 60 seconds.
"""

import os
import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/environment", tags=["environment"])


# ── Response schema ──────────────────────────────────────────────────────────

class EnvironmentStatusResponse(BaseModel):
    aqi: float | None
    temperature_celsius: float
    rainfall_mm_hr: float
    wind_speed_kmh: float
    humidity_pct: float
    threshold_breached: bool
    current_condition: str
    dominant_trigger: str | None   # "rainfall" | "aqi" | "heat" | None
    policy_id: str


# ── Thresholds (mirrors parametric model in risk engine) ─────────────────────

THRESHOLDS = {
    "rainfall_mm_hr": 35.0,     # >35 mm/hr sustained
    "aqi": 300.0,               # >300 NAQI
    "temperature_celsius": 44.0, # >44°C extreme heat
}


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.get("/status", response_model=EnvironmentStatusResponse)
async def get_environment_status(
    lat: float = Query(..., ge=-90, le=90, description="Worker latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Worker longitude"),
    policy_id: str = Query(default="", description="Active policy ID"),
):
    api_key = os.getenv("OPENWEATHER_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Weather API key not configured. Set OPENWEATHER_API_KEY in .env"
        )

    # ── Fetch weather data ───────────────────────────────────────────────────
    weather_url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    )

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(weather_url)
            res.raise_for_status()
            data = res.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"OpenWeatherMap error: {e.response.status_code}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach weather API: {str(e)}")

    # ── Parse fields ─────────────────────────────────────────────────────────
    temperature = round(data["main"]["temp"], 1)
    humidity = round(data["main"].get("humidity", 0), 1)
    wind_speed_ms = data["wind"].get("speed", 0)
    wind_speed_kmh = round(wind_speed_ms * 3.6, 1)
    rainfall_mm_hr = round(data.get("rain", {}).get("1h", 0.0), 2)
    condition_desc = data["weather"][0]["description"].title()

    # ── AQI: use OpenWeatherMap Air Pollution API (same key) ─────────────────
    aqi_value: float | None = None
    try:
        aqi_url = (
            f"https://api.openweathermap.org/data/2.5/air_pollution"
            f"?lat={lat}&lon={lon}&appid={api_key}"
        )
        async with httpx.AsyncClient(timeout=5.0) as client:
            aqi_res = await client.get(aqi_url)
            aqi_res.raise_for_status()
            aqi_data = aqi_res.json()
            # OWM AQI scale: 1=Good, 2=Fair, 3=Moderate, 4=Poor, 5=Very Poor
            # Convert to approximate NAQI (0–500) for threshold comparison
            owm_aqi = aqi_data["list"][0]["main"]["aqi"]
            aqi_value = round(float(owm_aqi) * 100, 1)  # approx mapping
    except Exception:
        # AQI is best-effort; don't fail the whole response
        aqi_value = None

    # ── Threshold evaluation ─────────────────────────────────────────────────
    breaches: dict[str, bool] = {
        "rainfall": rainfall_mm_hr > THRESHOLDS["rainfall_mm_hr"],
        "aqi": aqi_value is not None and aqi_value > THRESHOLDS["aqi"],
        "heat": temperature > THRESHOLDS["temperature_celsius"],
    }
    threshold_breached = any(breaches.values())
    dominant_trigger = next((k for k, v in breaches.items() if v), None)

    return EnvironmentStatusResponse(
        aqi=aqi_value,
        temperature_celsius=temperature,
        rainfall_mm_hr=rainfall_mm_hr,
        wind_speed_kmh=wind_speed_kmh,
        humidity_pct=humidity,
        threshold_breached=threshold_breached,
        current_condition=condition_desc,
        dominant_trigger=dominant_trigger,
        policy_id=policy_id,
    )