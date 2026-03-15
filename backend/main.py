"""
main.py
-------
GigGuard AI — FastAPI Backend

Entry point for the GigGuard AI backend server.
Exposes three REST endpoints that supply data to the frontend pages:

  GET /dashboard  → Worker Dashboard   (dashboard.html)
  GET /risk       → Risk Monitor page  (risk-monitor.html)
  GET /simulate   → Payout Simulation  (payout.html)

Additionally, two utility endpoints are provided:
  GET /           → health check / welcome
  GET /calculate  → custom risk + payout calculation via query params

Run the server with:
  uvicorn main:app --reload

Dependencies (install via pip):
  fastapi
  uvicorn[standard]
  pydantic
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

# Local modules
from risk_engine import calculate_risk
from payout_engine import calculate_payout, CoveragePlan
from data_service import (
    get_dashboard_data,
    get_current_environmental_data,
    get_simulated_event,
)


# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

app = FastAPI(
    title="GigGuard AI — Backend API",
    description=(
        "Parametric insurance platform for gig workers. "
        "Provides risk scoring and automatic payout calculation "
        "based on live environmental data."
    ),
    version="1.0.0",
    docs_url="/docs",       # Swagger UI at /docs
    redoc_url="/redoc",     # ReDoc UI  at /redoc
)


# ---------------------------------------------------------------------------
# CORS middleware
# Allows the frontend (any origin during development) to call these APIs.
# In production, replace ["*"] with your actual frontend domain(s).
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # e.g. ["https://gigguard.ai"] in production
    allow_credentials=True,
    allow_methods=["*"],        # GET, POST, OPTIONS, etc.
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic response models
# These define the exact shape of each endpoint's JSON response and also
# drive the auto-generated Swagger documentation.
# ---------------------------------------------------------------------------

class WorkerModel(BaseModel):
    id: str
    name: str
    platform: str
    zone: str
    status: str
    shift_started: str
    days_covered: int
    member_since: str

class PlanTriggersModel(BaseModel):
    rainfall_mm_per_hr: float
    aqi_ug_m3: float
    wind_speed_km_h: float

class PlanModel(BaseModel):
    plan_name: str
    plan_type: str
    premium_inr: float
    premium_period: str
    coverage_cap_inr: float
    max_claims_per_week: int
    claims_used_this_week: int
    valid_until: str
    claim_process: str
    triggers: PlanTriggersModel

class CurrentRiskModel(BaseModel):
    risk_score: float
    risk_level: str
    rainfall: float
    aqi: float
    wind_speed: float

class PayoutDeliveryModel(BaseModel):
    method: str
    upi_id_masked: str
    eta_hours: int

class PayoutStatusModel(BaseModel):
    triggered: bool
    amount_inr: float
    payout_percentage: float
    message: str
    delivery: PayoutDeliveryModel

class DashboardResponse(BaseModel):
    worker: WorkerModel
    plan: PlanModel
    current_risk: CurrentRiskModel
    payout_status: PayoutStatusModel
    last_updated: str


class ComponentScoresModel(BaseModel):
    rainfall_score: float
    aqi_score: float
    wind_score: float

class RiskResponse(BaseModel):
    rainfall: float
    aqi: float
    wind_speed: float
    scenario_label: str
    component_scores: ComponentScoresModel
    risk_score: float
    risk_level: str
    payout_triggered: bool
    payout_percentage: float
    gross_payout: float
    platform_fee: float
    payout: float
    payout_message: str
    timestamp: str


# RiskResponse and SimulateResponse share the same shape
SimulateResponse = RiskResponse


class CalculateResponse(BaseModel):
    """Response for the custom /calculate endpoint."""
    rainfall: float
    aqi: float
    wind_speed: float
    risk_score: float
    risk_level: str
    payout_triggered: bool
    payout_percentage: float
    payout: float
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get(
    "/",
    summary="Health check",
    tags=["Utility"],
)
def root():
    """
    Simple health check / welcome endpoint.
    Returns a status message confirming the API is running.
    """
    return {
        "service": "GigGuard AI Backend",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": ["/dashboard", "/risk", "/simulate", "/calculate"],
    }


@app.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Worker Dashboard data",
    tags=["Frontend"],
)
def dashboard():
    """
    Returns all data required by **dashboard.html**:

    - Worker profile (name, platform, zone, status)
    - Active insurance plan details
    - Latest environmental risk score & level
    - Payout trigger status and amount

    The risk score and payout are recomputed on every request using the
    latest environmental readings.
    """
    return get_dashboard_data()


@app.get(
    "/risk",
    response_model=RiskResponse,
    summary="Environmental risk monitoring data",
    tags=["Frontend"],
)
def risk():
    """
    Returns live environmental readings and the computed risk score.
    Powers **risk-monitor.html**.

    Includes:
    - Raw readings: rainfall, AQI, wind speed
    - Per-parameter normalised scores
    - Overall weighted risk score (0.0 – 1.0)
    - Risk level label: LOW / MEDIUM / HIGH / CRITICAL
    - Whether payout thresholds are met
    """
    return get_current_environmental_data()


@app.get(
    "/simulate",
    response_model=SimulateResponse,
    summary="Simulated disruption event & payout",
    tags=["Frontend"],
)
def simulate():
    """
    Returns a randomly generated disruption scenario and the resulting payout.
    Powers **payout.html** and allows hackathon judges to see different cases.

    Each call randomly picks from disruption / medium / calm scenario pools
    (weighted 60 / 20 / 20 %) so repeated calls demonstrate the full range
    of the payout engine.

    Example response for a disruption event:
    ```json
    {
      "rainfall": 70,
      "aqi": 280,
      "wind_speed": 20,
      "risk_score": 0.83,
      "payout": 500
    }
    ```
    """
    return get_simulated_event()


@app.get(
    "/calculate",
    response_model=CalculateResponse,
    summary="Custom risk & payout calculation",
    tags=["Utility"],
)
def calculate(
    rainfall: float = Query(
        default=50.0,
        ge=0, le=500,
        description="Rainfall intensity in mm/hr (0 – 500)",
    ),
    aqi: float = Query(
        default=200.0,
        ge=0, le=1000,
        description="Air Quality Index PM2.5 in µg/m³ (0 – 1000)",
    ),
    wind_speed: float = Query(
        default=30.0,
        ge=0, le=200,
        description="Wind speed in km/h (0 – 200)",
    ),
    coverage_cap: float = Query(
        default=2500.0,
        ge=500, le=10000,
        description="Worker's coverage cap in INR (500 – 10 000)",
    ),
):
    """
    Accept custom environmental values via query parameters and return
    the computed risk score and payout amount.

    This endpoint is useful for the interactive **Payout Simulator** slider
    on the frontend (payout.html) — the frontend can call:

        /calculate?rainfall=80&aqi=300&wind_speed=50&coverage_cap=2500

    and display the live result without any page reload.
    """

    # Guard against nonsensical inputs (FastAPI Query validators handle range)
    risk_result = calculate_risk(rainfall, aqi, wind_speed)

    plan = CoveragePlan(coverage_cap=coverage_cap)
    payout_result = calculate_payout(
        risk_result.risk_score, risk_result.risk_level, plan
    )

    return {
        "rainfall": rainfall,
        "aqi": aqi,
        "wind_speed": wind_speed,
        "risk_score": risk_result.risk_score,
        "risk_level": risk_result.risk_level,
        "payout_triggered": payout_result.payout_triggered,
        "payout_percentage": payout_result.payout_percentage,
        "payout": payout_result.net_payout,
        "message": payout_result.message,
    }
