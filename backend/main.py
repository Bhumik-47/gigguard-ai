"""
main.py
-------
GigGuard AI — FastAPI Backend  (v4 — Hackathon AI Layer)

All v3 endpoints are preserved and backward-compatible.
Pydantic models updated for v4 fields.

New fields in v4 responses
---------------------------
  trend / trend_velocity / slope / r_squared  — regression-based trend
  anomaly_flag / anomaly_severity / anomaly_details / max_z_score
  predicted_risk_score / predicted_risk_level
  risk_category_reason / decision_explanation
  risk_loading / claim_adjustment / final_payout / payout_explanation
  actuarial.event_probability / expected_loss / dynamic_premium
  fraud_check.fraud_score (0-1) / fraud_flag (bool) / fraud_explanation

Run:
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
        "Parametric insurance for gig workers. "
        "v4: Rolling-window trend detection · Z-score anomaly detection · "
        "Predictive risk scoring · Dynamic premium pricing · "
        "Risk-loaded payouts · Fraud intelligence with pattern memory."
    ),
    version="4.0.0",
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
    exclusions_summary: list[str]


class ComponentScoresModel(BaseModel):
    rainfall_score: float; aqi_score: float; wind_score: float


class IMDBandsModel(BaseModel):
    rainfall: str; aqi: str; wind_speed: str


class ConfidenceModel(BaseModel):
    score: float; label: str


class RiskTrendModel(BaseModel):
    trend: str; message: str
    eta_hours: Optional[int]
    contributing_factors: list[str]
    confidence: float


class ExclusionModel(BaseModel):
    is_excluded: bool; exclusion_code: str; reason: str
    is_partial: bool; reduction_pct: float
    applicable_clauses: list[str]


class FraudFlagModel(BaseModel):
    rule_code: str; weight: int; description: str


class FraudCheckModel(BaseModel):
    raw_score:         int
    fraud_score:       float    # 0.0–1.0 (v4)
    fraud_flag:        bool     # v4
    verdict:           str
    flag_codes:        list[str]
    reason:            str
    fraud_explanation: str      # v4
    auto_approve:      bool
    flags:             list[FraudFlagModel]


class ActuarialModel(BaseModel):
    pure_premium:           Optional[float]
    loaded_premium:         Optional[float]
    premium_adequacy:       Optional[str]
    expected_loss_ratio:    Optional[float]
    claims_reserve:         Optional[float]
    expected_weekly_payout: Optional[float]
    # v4 NEW
    event_probability:  Optional[float]
    expected_loss:      Optional[float]
    dynamic_premium:    Optional[float]
    risk_loading:       Optional[float]
    claim_adjustment:   Optional[float]


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
    # v4
    trend: str; trend_velocity: float
    anomaly_flag: bool; anomaly_severity: str
    predicted_risk_score: float; predicted_risk_level: str
    risk_category_reason: str; decision_explanation: str


class PayoutStatusModel(BaseModel):
    triggered: bool; tier_label: str; payout_percentage: float
    gross_payout: float; platform_fee: float; net_payout: float
    # v4
    risk_loading: float; claim_adjustment: float; final_payout: float
    effective_payout: float; amount_inr: float
    payout_explanation: str
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
    # v4
    trend: str; trend_velocity: float; slope: float; r_squared: float
    anomaly_flag: bool; anomaly_severity: str
    anomaly_details: list[str]; max_z_score: float
    predicted_risk_score: float; predicted_risk_level: str
    risk_category_reason: str; decision_explanation: str
    # payout
    payout_triggered: bool; tier_label: str; tier_desc: str
    payout_percentage: float; coverage_cap: float
    gross_payout: float; platform_fee: float; net_payout: float
    risk_loading: float; claim_adjustment: float; final_payout: float
    effective_payout: float; payout: float
    payout_message: str; payout_explanation: str
    exclusion_applied: bool; adjusted_net_payout: float
    actuarial: ActuarialModel; fraud_check: FraudCheckModel
    timestamp: str


SimulateResponse = RiskResponse


class CalculateResponse(BaseModel):
    rainfall: float; aqi: float; wind_speed: float
    risk_score: float; risk_level: str; primary_hazard: str
    imd_bands: IMDBandsModel; confidence: ConfidenceModel
    risk_trend: RiskTrendModel
    # v4
    trend: str; trend_velocity: float
    anomaly_flag: bool; anomaly_severity: str
    predicted_risk_score: float; predicted_risk_level: str
    risk_category_reason: str; decision_explanation: str
    # payout
    payout_triggered: bool; tier_label: str
    payout_percentage: float; coverage_cap: float
    gross_payout: float; platform_fee: float; net_payout: float
    risk_loading: float; claim_adjustment: float; final_payout: float
    payout: float
    exclusion: ExclusionModel; fraud_check: FraudCheckModel
    actuarial: ActuarialModel
    payout_explanation: str; message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", summary="Health check", tags=["Utility"])
def root():
    return {
        "service": "GigGuard AI Backend", "status": "running", "version": "4.0.0",
        "docs": "/docs",
        "endpoints": ["/dashboard", "/risk", "/simulate", "/calculate"],
        "v4_ai_features": [
            "Rolling window (10 observations) risk score memory",
            "Linear regression trend detection: increasing / stable / decreasing",
            "Trend velocity (slope magnitude) for UI sparklines",
            "Z-score anomaly detection per environmental parameter",
            "Predictive risk score (extrapolated 3 steps ahead)",
            "Decision explanation — natural language AI narrative",
            "Dynamic premium pricing: base × (1 + risk_score)",
            "Event probability table: P(disruption | risk_score)",
            "Expected loss calculation: P(event) × coverage_cap",
            "Risk loading factor: base + anomaly surcharge + repeat claim loading",
            "Claim frequency payout tapering: 100% → 80% → 60% → 40%",
            "Fraud pattern memory via rolling buffer correlation",
            "Normalised fraud_score 0.0–1.0 + fraud_flag boolean",
            "7 fraud rules including anomaly correlation + persistent near-threshold",
        ],
    }


@app.get("/dashboard", response_model=DashboardResponse,
         summary="Worker Dashboard", tags=["Frontend"])
def dashboard():
    """Full dashboard payload including all v4 AI and actuarial fields."""
    return get_dashboard_data()


@app.get("/risk", response_model=RiskResponse,
         summary="Environmental risk monitoring", tags=["Frontend"])
def risk():
    """Live risk data with trend analysis, anomaly detection, and prediction."""
    return get_current_environmental_data()


@app.get("/simulate", response_model=SimulateResponse,
         summary="Simulated disruption event", tags=["Frontend"])
def simulate():
    """Random scenario — 60% disruption / 20% medium / 20% calm."""
    return get_simulated_event()


@app.get("/calculate", response_model=CalculateResponse,
         summary="Custom risk & payout calculation", tags=["Utility"])
def calculate(
    rainfall: float = Query(default=50.0, ge=0, le=500,
                            description="Rainfall intensity mm/hr"),
    aqi: float = Query(default=200.0, ge=0, le=1000,
                       description="AQI PM2.5 µg/m³"),
    wind_speed: float = Query(default=30.0, ge=0, le=200,
                              description="Wind speed km/h"),
    coverage_cap: float = Query(default=2500.0, ge=500, le=10000,
                                description="Coverage cap INR"),
    claims_this_week: int = Query(default=0, ge=0, le=10,
                                  description="Claims filed this week"),
):
    """
    Full engine pipeline via query params.
    Example: /calculate?rainfall=80&aqi=300&wind_speed=55&claims_this_week=1
    """
    risk_r  = calculate_risk(rainfall, aqi, wind_speed)
    trend_r = predict_risk_trend(rainfall, aqi, wind_speed)

    ctx  = ClaimContext(claims_this_week=claims_this_week)
    excl = evaluate_exclusions(ctx)

    plan   = CoveragePlan(coverage_cap=coverage_cap)
    payout = calculate_payout(
        risk_r.risk_score, risk_r.risk_level, plan,
        anomaly_detected=risk_r.anomaly_flag,
        claims_this_period=claims_this_week + 1,
    )
    if excl.is_excluded:
        payout = apply_exclusion_to_payout(
            payout, excl.exclusion_code, excl.is_partial,
            excl.reduction_pct, excl.reason,
        )

    fraud = detect_fraud(
        payout_triggered=payout.payout_triggered,
        risk_score=risk_r.risk_score,
        rainfall=rainfall, aqi=aqi, wind_speed=wind_speed,
        rainfall_score=risk_r.rainfall_score,
        aqi_score=risk_r.aqi_score,
        wind_score=risk_r.wind_score,
        claims_this_week=claims_this_week,
        anomaly_flag=risk_r.anomaly_flag,
    )

    effective = payout.adjusted_net_payout if excl.is_excluded else payout.final_payout
    if fraud.verdict in ("BLOCKED", "SUSPICIOUS"):
        effective = 0.0

    act = payout.actuarial

    return {
        "rainfall": rainfall, "aqi": aqi, "wind_speed": wind_speed,
        "risk_score":     risk_r.risk_score,
        "risk_level":     risk_r.risk_level,
        "primary_hazard": risk_r.primary_hazard,
        "imd_bands": {"rainfall": risk_r.rainfall_band,
                      "aqi": risk_r.aqi_band, "wind_speed": risk_r.wind_band},
        "confidence": {"score": risk_r.confidence, "label": risk_r.confidence_label},
        "risk_trend": {"trend": trend_r.trend, "message": trend_r.message,
                       "eta_hours": trend_r.eta_hours,
                       "contributing_factors": trend_r.contributing_factors,
                       "confidence": trend_r.confidence},
        # v4 AI fields
        "trend":          risk_r.trend,
        "trend_velocity": risk_r.trend_velocity,
        "anomaly_flag":     risk_r.anomaly_flag,
        "anomaly_severity": risk_r.anomaly_severity,
        "predicted_risk_score": risk_r.predicted_risk_score,
        "predicted_risk_level": risk_r.predicted_risk_level,
        "risk_category_reason": risk_r.risk_category_reason,
        "decision_explanation": risk_r.decision_explanation,
        # payout
        "payout_triggered":  payout.payout_triggered,
        "tier_label":        payout.tier_label,
        "payout_percentage": payout.payout_percentage,
        "coverage_cap":      payout.coverage_cap,
        "gross_payout":      payout.gross_payout,
        "platform_fee":      payout.platform_fee,
        "net_payout":        payout.net_payout,
        "risk_loading":      payout.risk_loading,
        "claim_adjustment":  payout.claim_adjustment,
        "final_payout":      payout.final_payout,
        "payout":            effective,
        "exclusion": {
            "is_excluded": excl.is_excluded, "exclusion_code": excl.exclusion_code,
            "reason": excl.reason, "is_partial": excl.is_partial,
            "reduction_pct": excl.reduction_pct,
            "applicable_clauses": excl.applicable_clauses,
        },
        "fraud_check": {
            "raw_score": fraud.raw_score, "fraud_score": fraud.fraud_score,
            "fraud_flag": fraud.fraud_flag, "verdict": fraud.verdict,
            "flag_codes": fraud.flag_codes, "reason": fraud.reason,
            "fraud_explanation": fraud.fraud_explanation,
            "auto_approve": fraud.auto_approve,
            "flags": [{"rule_code": f.rule_code, "weight": f.weight,
                       "description": f.description} for f in fraud.flags],
        },
        "actuarial": {
            "pure_premium":          act.pure_premium           if act else None,
            "loaded_premium":        act.loaded_premium         if act else None,
            "premium_adequacy":      act.premium_adequacy       if act else None,
            "expected_loss_ratio":   act.expected_loss_ratio    if act else None,
            "claims_reserve":        act.claims_reserve         if act else None,
            "expected_weekly_payout":act.expected_weekly_payout if act else None,
            "event_probability":     act.event_probability      if act else None,
            "expected_loss":         act.expected_loss          if act else None,
            "dynamic_premium":       act.dynamic_premium        if act else None,
            "risk_loading":          act.risk_loading           if act else None,
            "claim_adjustment":      act.claim_adjustment       if act else None,
        },
        "payout_explanation": payout.payout_explanation,
        "message": payout.message,
    }
