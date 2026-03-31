"""
main.py
-------
GigGuard AI — FastAPI Backend  (v3)

All v1 endpoints are preserved and backward-compatible.
Pydantic response models updated to reflect v3 engine outputs.

New fields in v3 responses
---------------------------
  imd_bands           — IMD/CPCB band classification per raw reading
  confidence          — Prediction confidence score + label
  primary_hazard      — Which factor is dominating the risk score
  risk_trend          — Trend label, forecast message, ETA hours, confidence
  exclusion           — Full exclusion evaluation (SAFE or clause details)
  tier_label/tier_desc— Payout tier classification (MILD/SIGNIFICANT/CRITICAL)
  coverage_cap        — Policy coverage cap surfaced for UI transparency
  gross_payout        — Pre-fee payout amount
  platform_fee        — 10% fee deducted
  net_payout          — Amount worker receives
  effective_payout    — Net after exclusion adjustment + fraud filter
  actuarial           — Actuarial model: pure premium, loss ratio, reserve
  fraud_check         — 4-level verdict with fraud_score + flag detail

Run with:
  uvicorn main:app --reload
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from risk_engine   import calculate_risk, predict_risk_trend
from exclusions    import evaluate_exclusions, ClaimContext
from payout_engine import calculate_payout, apply_exclusion_to_payout, CoveragePlan
from fraud_engine  import detect_fraud
from data_service  import (
    get_dashboard_data,
    get_current_environmental_data,
    get_simulated_event,
)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="GigGuard AI — Backend API",
    description=(
        "Parametric insurance platform for gig workers. "
        "v3: AI risk scoring · IMD/CPCB classification · Actuarial modeling · "
        "IRDAI-compliant exclusions (war/pandemic) · Multi-rule fraud detection."
    ),
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic sub-models
# ---------------------------------------------------------------------------

class WorkerModel(BaseModel):
    id: str; name: str; platform: str; zone: str
    status: str; shift_started: str; days_covered: int; member_since: str


class PlanTriggersModel(BaseModel):
    rainfall_mm_per_hr: float; aqi_ug_m3: float; wind_speed_km_h: float


class PlanModel(BaseModel):
    plan_name: str; plan_type: str; premium_inr: float; premium_period: str
    coverage_cap_inr: float; max_claims_per_week: int; claims_used_this_week: int
    valid_until: str; claim_process: str; triggers: PlanTriggersModel
    exclusions_summary: list[str]           # v3 NEW


class ComponentScoresModel(BaseModel):
    rainfall_score: float; aqi_score: float; wind_score: float


class IMDBandsModel(BaseModel):            # v3 NEW
    rainfall: str; aqi: str; wind_speed: str


class ConfidenceModel(BaseModel):          # v3 NEW
    score: float; label: str


class RiskTrendModel(BaseModel):           # v3 NEW
    trend: str; message: str
    eta_hours: Optional[int]
    contributing_factors: list[str]
    confidence: float


class ExclusionModel(BaseModel):           # v3 NEW
    is_excluded: bool; exclusion_code: str; reason: str
    is_partial: bool; reduction_pct: float
    applicable_clauses: list[str]


class FraudFlagModel(BaseModel):           # v3 NEW
    rule_code: str; weight: int; description: str


class FraudCheckModel(BaseModel):          # v3 NEW (4-level verdict)
    fraud_score: int
    verdict: str                           # SAFE | REVIEW | SUSPICIOUS | BLOCKED
    flag_codes: list[str]
    reason: str
    auto_approve: bool
    flags: list[FraudFlagModel]


class ActuarialModel(BaseModel):           # v3 NEW
    pure_premium: Optional[float]
    loaded_premium: Optional[float]
    premium_adequacy: Optional[str]
    expected_loss_ratio: Optional[float]
    claims_reserve: Optional[float]
    expected_weekly_payout: Optional[float]


class PayoutDeliveryModel(BaseModel):
    method: str; upi_id_masked: str; eta_hours: int


# ---------------------------------------------------------------------------
# Endpoint response models
# ---------------------------------------------------------------------------

class CurrentRiskModel(BaseModel):
    risk_score: float; risk_level: str; primary_hazard: str
    rainfall: float; aqi: float; wind_speed: float
    imd_bands: IMDBandsModel; confidence: ConfidenceModel
    risk_trend: RiskTrendModel


class PayoutStatusModel(BaseModel):
    triggered: bool; tier_label: str; payout_percentage: float
    gross_payout: float; platform_fee: float
    net_payout: float; effective_payout: float; amount_inr: float
    exclusion: ExclusionModel; fraud_check: FraudCheckModel
    message: str; delivery: PayoutDeliveryModel


class DashboardResponse(BaseModel):
    worker: WorkerModel; plan: PlanModel
    current_risk: CurrentRiskModel; payout_status: PayoutStatusModel
    actuarial: ActuarialModel; last_updated: str


class RiskResponse(BaseModel):
    rainfall: float; aqi: float; wind_speed: float; scenario_label: str
    component_scores: ComponentScoresModel
    risk_score: float; risk_level: str; primary_hazard: str
    imd_bands: IMDBandsModel; confidence: ConfidenceModel
    risk_trend: RiskTrendModel; exclusion: ExclusionModel
    payout_triggered: bool; tier_label: str; tier_desc: str
    payout_percentage: float; coverage_cap: float
    gross_payout: float; platform_fee: float
    net_payout: float; effective_payout: float; payout: float
    payout_message: str; exclusion_applied: bool
    adjusted_net_payout: float; actuarial: ActuarialModel
    fraud_check: FraudCheckModel; timestamp: str


SimulateResponse = RiskResponse


class CalculateResponse(BaseModel):
    rainfall: float; aqi: float; wind_speed: float
    risk_score: float; risk_level: str; primary_hazard: str
    imd_bands: IMDBandsModel; confidence: ConfidenceModel
    risk_trend: RiskTrendModel
    payout_triggered: bool; tier_label: str
    payout_percentage: float; coverage_cap: float
    gross_payout: float; platform_fee: float
    net_payout: float; payout: float
    exclusion: ExclusionModel; fraud_check: FraudCheckModel
    actuarial: ActuarialModel; message: str


# ---------------------------------------------------------------------------
# Routes — all v1 endpoints preserved
# ---------------------------------------------------------------------------

@app.get("/", summary="Health check", tags=["Utility"])
def root():
    """Health check confirming the API is running."""
    return {
        "service": "GigGuard AI Backend",
        "status":  "running",
        "version": "3.0.0",
        "docs":    "/docs",
        "endpoints": ["/dashboard", "/risk", "/simulate", "/calculate"],
        "v3_features": [
            "Non-linear severity amplification (power-law exponent 1.4)",
            "IMD rainfall + CPCB AQI + Beaufort wind band classification",
            "Prediction confidence scoring (agreement across factors)",
            "Risk trend forecasting with ETA hours",
            "IRDAI-compliant exclusions: pandemic, war, claim limits, govt restriction",
            "Actuarial model: pure premium, loss ratio, claims reserve",
            "Multi-rule fraud detection — 4-level verdict (SAFE/REVIEW/SUSPICIOUS/BLOCKED)",
            "Explicit gross → platform_fee(10%) → net payout breakdown",
        ],
    }


@app.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Worker Dashboard data",
    tags=["Frontend"],
)
def dashboard():
    """
    Full dashboard payload for dashboard.html.
    Includes: risk score, trend + ETA, exclusion status, payout breakdown
    with gross/fee/net, actuarial model, and 4-level fraud verdict.
    """
    return get_dashboard_data()


@app.get(
    "/risk",
    response_model=RiskResponse,
    summary="Environmental risk monitoring",
    tags=["Frontend"],
)
def risk():
    """
    Live environmental risk data for risk-monitor.html.
    Includes IMD/CPCB band classification, confidence score,
    trend forecast with ETA, and the full engine pipeline output.
    """
    return get_current_environmental_data()


@app.get(
    "/simulate",
    response_model=SimulateResponse,
    summary="Simulated disruption event",
    tags=["Frontend"],
)
def simulate():
    """
    Random scenario for payout.html demo.
    Pools: 60% disruption / 20% medium / 20% calm.
    Call multiple times to see the full range of engine outputs.
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
        default=50.0, ge=0, le=500,
        description="Rainfall intensity mm/hr",
    ),
    aqi: float = Query(
        default=200.0, ge=0, le=1000,
        description="AQI PM2.5 µg/m³",
    ),
    wind_speed: float = Query(
        default=30.0, ge=0, le=200,
        description="Wind speed km/h",
    ),
    coverage_cap: float = Query(
        default=2500.0, ge=500, le=10000,
        description="Coverage cap INR",
    ),
    claims_this_week: int = Query(
        default=0, ge=0, le=10,
        description="Claims filed this week (for exclusion + fraud checks)",
    ),
):
    """
    Custom calculation via query params — runs the full engine pipeline.
    Useful for the interactive simulator slider on payout.html.

    Example:
        /calculate?rainfall=80&aqi=300&wind_speed=55&coverage_cap=2500&claims_this_week=1
    """
    # 1. Risk
    risk_r  = calculate_risk(rainfall, aqi, wind_speed)
    trend_r = predict_risk_trend(rainfall, aqi, wind_speed)

    # 2. Exclusion
    ctx  = ClaimContext(claims_this_week=claims_this_week)
    excl = evaluate_exclusions(ctx)

    # 3. Payout + exclusion adjustment
    plan   = CoveragePlan(coverage_cap=coverage_cap)
    payout = calculate_payout(risk_r.risk_score, risk_r.risk_level, plan)
    if excl.is_excluded:
        payout = apply_exclusion_to_payout(
            payout, excl.exclusion_code, excl.is_partial,
            excl.reduction_pct, excl.reason,
        )

    # 4. Fraud
    fraud = detect_fraud(
        payout_triggered=payout.payout_triggered,
        risk_score=risk_r.risk_score,
        rainfall=rainfall, aqi=aqi, wind_speed=wind_speed,
        rainfall_score=risk_r.rainfall_score,
        aqi_score=risk_r.aqi_score,
        wind_score=risk_r.wind_score,
        claims_this_week=claims_this_week,
    )

    effective = payout.adjusted_net_payout if excl.is_excluded else payout.net_payout
    if fraud.verdict in ("BLOCKED", "SUSPICIOUS"):
        effective = 0.0

    act = payout.actuarial

    return {
        "rainfall": rainfall, "aqi": aqi, "wind_speed": wind_speed,
        "risk_score":     risk_r.risk_score,
        "risk_level":     risk_r.risk_level,
        "primary_hazard": risk_r.primary_hazard,
        "imd_bands": {
            "rainfall":  risk_r.rainfall_band,
            "aqi":       risk_r.aqi_band,
            "wind_speed":risk_r.wind_band,
        },
        "confidence": {
            "score": risk_r.confidence,
            "label": risk_r.confidence_label,
        },
        "risk_trend": {
            "trend":                trend_r.trend,
            "message":              trend_r.message,
            "eta_hours":            trend_r.eta_hours,
            "contributing_factors": trend_r.contributing_factors,
            "confidence":           trend_r.confidence,
        },
        "payout_triggered":  payout.payout_triggered,
        "tier_label":        payout.tier_label,
        "payout_percentage": payout.payout_percentage,
        "coverage_cap":      payout.coverage_cap,
        "gross_payout":      payout.gross_payout,
        "platform_fee":      payout.platform_fee,
        "net_payout":        payout.net_payout,
        "payout":            effective,
        "exclusion": {
            "is_excluded":        excl.is_excluded,
            "exclusion_code":     excl.exclusion_code,
            "reason":             excl.reason,
            "is_partial":         excl.is_partial,
            "reduction_pct":      excl.reduction_pct,
            "applicable_clauses": excl.applicable_clauses,
        },
        "fraud_check": {
            "fraud_score":  fraud.fraud_score,
            "verdict":      fraud.verdict,
            "flag_codes":   fraud.flag_codes,
            "reason":       fraud.reason,
            "auto_approve": fraud.auto_approve,
            "flags": [
                {"rule_code": f.rule_code, "weight": f.weight,
                 "description": f.description}
                for f in fraud.flags
            ],
        },
        "actuarial": {
            "pure_premium":          act.pure_premium           if act else None,
            "loaded_premium":        act.loaded_premium         if act else None,
            "premium_adequacy":      act.premium_adequacy       if act else None,
            "expected_loss_ratio":   act.expected_loss_ratio    if act else None,
            "claims_reserve":        act.claims_reserve         if act else None,
            "expected_weekly_payout":act.expected_weekly_payout if act else None,
        },
        "message": payout.message,
    }
