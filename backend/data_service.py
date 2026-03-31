"""
data_service.py
---------------
GigGuard AI — Data Service  (v4)

Orchestration order (unchanged):
  1. risk_engine   → calculate_risk()  [now returns trend, anomaly, predicted_score]
  2. predict_risk_trend()
  3. exclusions    → evaluate_exclusions()
  4. payout_engine → calculate_payout() [now takes anomaly_detected + claims_this_period]
  5. apply_exclusion_to_payout()
  6. fraud_engine  → detect_fraud()    [now takes anomaly_flag]

All v3 public function signatures are preserved unchanged.
"""

import random
from datetime import datetime, date
import requests

from risk_engine   import calculate_risk, predict_risk_trend, RiskResult, TrendResult
from exclusions    import evaluate_exclusions, ClaimContext, ExclusionResult
from payout_engine import (
    calculate_payout, apply_exclusion_to_payout,
    CoveragePlan, PayoutResult,
)
from fraud_engine  import detect_fraud, FraudResult


# ---------------------------------------------------------------------------
# External API config
# ---------------------------------------------------------------------------
_OWM_API_KEY = "42d50818462ba415d9bb917acb935f72"


# ---------------------------------------------------------------------------
# Static data (unchanged from v3)
# ---------------------------------------------------------------------------

WORKER_PROFILE = {
    "id":            "SWG-09124",
    "name":          "Ravi Kumar",
    "platform":      "Swiggy",
    "zone":          "Delhi NCR — Laxmi Nagar",
    "status":        "Active",
    "shift_started": "09:30 AM",
    "days_covered":  47,
    "member_since":  "Jan 2025",
}

COVERAGE_PLAN = {
    "plan_name":              "Weekly Shield",
    "plan_type":              "Parametric Weather Insurance",
    "premium_inr":            49,
    "premium_period":         "week",
    "coverage_cap_inr":       2500,
    "max_claims_per_week":    2,
    "claims_used_this_week":  1,
    "claims_used_this_month": 3,
    "max_claims_per_month":   6,
    "valid_until":            str(date(2026, 3, 16)),
    "claim_process":          "Fully Automatic",
    "triggers": {
        "rainfall_mm_per_hr": 50,
        "aqi_ug_m3":          250,
        "wind_speed_km_h":    45,
    },
    "exclusions_summary": [
        "Pandemic / Government-declared health emergency (Section 4a)",
        "War, armed conflict, riots, curfew (Section 4b)",
        "Platform downtime — 50% reduction (Section 4c)",
        "Government restriction: odd-even, NGT ban — 50% reduction (Section 4d)",
        "More than 2 claims per week (Section 5a)",
        "More than 6 claims per month (Section 5a)",
        "Lapsed policy — unpaid premium (Section 2a)",
        "Account under fraud investigation (Section 6b)",
    ],
}

PAYOUT_DELIVERY = {
    "method":        "UPI Auto-Transfer",
    "upi_id_masked": "rkumar**91@upi",
    "eta_hours":     2,
}

_DEFAULT_CLAIM_CTX = ClaimContext(
    claims_this_week=    COVERAGE_PLAN["claims_used_this_week"],
    max_claims_per_week= COVERAGE_PLAN["max_claims_per_week"],
    claims_this_month=   COVERAGE_PLAN["claims_used_this_month"],
    max_claims_per_month=COVERAGE_PLAN["max_claims_per_month"],
    policy_active=True,
    is_pandemic_period=False,
    is_war_period=False,
    platform_outage=False,
    govt_restriction=False,
    worker_flagged=False,
)


# ---------------------------------------------------------------------------
# Scenario library (unchanged)
# ---------------------------------------------------------------------------

_DISRUPTION_SCENARIOS = [
    {"rainfall": 87.0,  "aqi": 312.0, "wind_speed": 54.0, "label": "Heavy monsoon + smog"},
    {"rainfall": 95.0,  "aqi": 280.0, "wind_speed": 60.0, "label": "Cyclonic rainfall"},
    {"rainfall": 120.0, "aqi": 390.0, "wind_speed": 72.0, "label": "Extreme storm event"},
]
_MEDIUM_SCENARIOS = [
    {"rainfall": 35.0, "aqi": 200.0, "wind_speed": 35.0, "label": "Moderate pollution + rain"},
    {"rainfall": 45.0, "aqi": 230.0, "wind_speed": 40.0, "label": "Pre-monsoon haze"},
]
_CALM_SCENARIOS = [
    {"rainfall": 5.0, "aqi": 80.0,  "wind_speed": 12.0, "label": "Clear morning"},
    {"rainfall": 0.0, "aqi": 60.0,  "wind_speed": 8.0,  "label": "Sunny day"},
]


# ---------------------------------------------------------------------------
# Real weather API (unchanged)
# ---------------------------------------------------------------------------

def get_weather_by_location(lat: float, lon: float) -> dict:
    url = (
        f"https://api.openweathermap.org/data/2.5/weather?"
        f"lat={lat}&lon={lon}&appid={_OWM_API_KEY}&units=metric"
    )
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        return {
            "rainfall":    data.get("rain", {}).get("1h", 0.0),
            "wind_speed":  data["wind"]["speed"],
            "temperature": data["main"]["temp"],
            "humidity":    data["main"]["humidity"],
        }
    except Exception:
        return {"rainfall": 0.0, "wind_speed": 5.0, "temperature": 30.0, "humidity": 50.0}


# ---------------------------------------------------------------------------
# Core payload builder — v4
# ---------------------------------------------------------------------------

def _build_env_payload(
    rainfall:   float,
    aqi:        float,
    wind_speed: float,
    label:      str = "",
    claim_ctx:  ClaimContext = _DEFAULT_CLAIM_CTX,
) -> dict:
    """
    Orchestrates all four engines and assembles the full v4 response dict.

    New fields added in v4 (beyond v3)
    ------------------------------------
    From risk_engine:
      trend, trend_velocity, slope, r_squared
      anomaly_flag, anomaly_severity, anomaly_details, max_z_score
      predicted_risk_score, predicted_risk_level
      risk_category_reason, decision_explanation

    From payout_engine:
      risk_loading, claim_adjustment, final_payout
      payout_explanation
      actuarial.event_probability, actuarial.expected_loss,
      actuarial.dynamic_premium, actuarial.risk_loading, actuarial.claim_adjustment

    From fraud_engine:
      raw_score, fraud_score, fraud_flag, fraud_explanation
    """

    # ── 1. Risk engine (v4 — now returns trend + anomaly + predicted) ─────
    risk:  RiskResult  = calculate_risk(rainfall, aqi, wind_speed)
    trend: TrendResult = predict_risk_trend(rainfall, aqi, wind_speed)

    # ── 2. Exclusion engine ───────────────────────────────────────────────
    exclusion: ExclusionResult = evaluate_exclusions(claim_ctx)

    # ── 3. Payout engine (v4 — passes anomaly + claim count) ─────────────
    plan = CoveragePlan(
        plan_name=           COVERAGE_PLAN["plan_name"],
        coverage_cap=        COVERAGE_PLAN["coverage_cap_inr"],
        premium=             COVERAGE_PLAN["premium_inr"],
        max_claims_per_week= COVERAGE_PLAN["max_claims_per_week"],
        max_claims_per_month=COVERAGE_PLAN["max_claims_per_month"],
    )
    payout: PayoutResult = calculate_payout(
        risk.risk_score, risk.risk_level, plan,
        include_actuarial=True,
        anomaly_detected=risk.anomaly_flag,
        claims_this_period=claim_ctx.claims_this_week + 1,
    )

    if exclusion.is_excluded:
        payout = apply_exclusion_to_payout(
            payout, exclusion.exclusion_code, exclusion.is_partial,
            exclusion.reduction_pct, exclusion.reason,
        )

    effective = payout.adjusted_net_payout if exclusion.is_excluded else payout.final_payout

    # ── 4. Fraud engine (v4 — passes anomaly_flag) ────────────────────────
    fraud: FraudResult = detect_fraud(
        payout_triggered=    payout.payout_triggered,
        risk_score=          risk.risk_score,
        rainfall=            rainfall,
        aqi=                 aqi,
        wind_speed=          wind_speed,
        rainfall_score=      risk.rainfall_score,
        aqi_score=           risk.aqi_score,
        wind_score=          risk.wind_score,
        claims_this_week=    claim_ctx.claims_this_week,
        max_claims_per_week= claim_ctx.max_claims_per_week,
        anomaly_flag=        risk.anomaly_flag,
    )

    if fraud.verdict in ("BLOCKED", "SUSPICIOUS"):
        effective = 0.0

    act = payout.actuarial

    return {
        # Raw readings
        "rainfall":       rainfall,
        "aqi":            aqi,
        "wind_speed":     wind_speed,
        "scenario_label": label,

        # ── Risk engine ───────────────────────────────────────────────────
        "component_scores": {
            "rainfall_score": risk.rainfall_score,
            "aqi_score":      risk.aqi_score,
            "wind_score":     risk.wind_score,
        },
        "risk_score":     risk.risk_score,
        "risk_level":     risk.risk_level,
        "primary_hazard": risk.primary_hazard,
        "imd_bands": {
            "rainfall":   risk.rainfall_band,
            "aqi":        risk.aqi_band,
            "wind_speed": risk.wind_band,
        },
        "confidence": {
            "score": risk.confidence,
            "label": risk.confidence_label,
        },

        # ── v4 AI outputs ─────────────────────────────────────────────────
        "trend":          risk.trend,           # "increasing"|"stable"|"decreasing"
        "trend_velocity": risk.trend_velocity,
        "slope":          risk.slope,
        "r_squared":      risk.r_squared,

        "anomaly_flag":     risk.anomaly_flag,
        "anomaly_severity": risk.anomaly_severity,
        "anomaly_details":  risk.anomaly_details,
        "max_z_score":      risk.max_z_score,

        "predicted_risk_score": risk.predicted_risk_score,
        "predicted_risk_level": risk.predicted_risk_level,

        "risk_category_reason": risk.risk_category_reason,
        "decision_explanation": risk.decision_explanation,

        # ── Trend (heuristic) ─────────────────────────────────────────────
        "risk_trend": {
            "trend":                trend.trend,
            "message":              trend.message,
            "eta_hours":            trend.eta_hours,
            "contributing_factors": trend.contributing_factors,
            "confidence":           trend.confidence,
        },

        # ── Exclusion ─────────────────────────────────────────────────────
        "exclusion": {
            "is_excluded":        exclusion.is_excluded,
            "exclusion_code":     exclusion.exclusion_code,
            "reason":             exclusion.reason,
            "is_partial":         exclusion.is_partial,
            "reduction_pct":      exclusion.reduction_pct,
            "applicable_clauses": exclusion.applicable_clauses,
        },

        # ── Payout ────────────────────────────────────────────────────────
        "payout_triggered":    payout.payout_triggered,
        "tier_label":          payout.tier_label,
        "tier_desc":           payout.tier_desc,
        "payout_percentage":   payout.payout_percentage,
        "coverage_cap":        payout.coverage_cap,
        "gross_payout":        payout.gross_payout,
        "platform_fee":        payout.platform_fee,
        "net_payout":          payout.net_payout,

        # v4 payout additions
        "risk_loading":        payout.risk_loading,
        "claim_adjustment":    payout.claim_adjustment,
        "final_payout":        payout.final_payout,
        "effective_payout":    effective,
        "payout":              effective,       # v1/v2/v3 compat
        "payout_message":      payout.message,
        "payout_explanation":  payout.payout_explanation,
        "exclusion_applied":   payout.exclusion_applied,
        "adjusted_net_payout": payout.adjusted_net_payout,

        # ── Actuarial ─────────────────────────────────────────────────────
        "actuarial": {
            "pure_premium":           act.pure_premium           if act else None,
            "loaded_premium":         act.loaded_premium         if act else None,
            "premium_adequacy":       act.premium_adequacy       if act else None,
            "expected_loss_ratio":    act.expected_loss_ratio    if act else None,
            "claims_reserve":         act.claims_reserve         if act else None,
            "expected_weekly_payout": act.expected_weekly_payout if act else None,
            # v4 NEW actuarial fields
            "event_probability":      act.event_probability      if act else None,
            "expected_loss":          act.expected_loss          if act else None,
            "dynamic_premium":        act.dynamic_premium        if act else None,
            "risk_loading":           act.risk_loading           if act else None,
            "claim_adjustment":       act.claim_adjustment       if act else None,
        },

        # ── Fraud ─────────────────────────────────────────────────────────
        "fraud_check": {
            "raw_score":        fraud.raw_score,
            "fraud_score":      fraud.fraud_score,       # 0.0–1.0 (v4)
            "fraud_flag":       fraud.fraud_flag,        # bool (v4)
            "verdict":          fraud.verdict,
            "flag_codes":       fraud.flag_codes,
            "reason":           fraud.reason,
            "fraud_explanation":fraud.fraud_explanation, # v4
            "auto_approve":     fraud.auto_approve,
            "flags": [
                {"rule_code": f.rule_code, "weight": f.weight,
                 "description": f.description}
                for f in fraud.flags
            ],
        },

        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ---------------------------------------------------------------------------
# Public service functions — all v3 signatures preserved
# ---------------------------------------------------------------------------

def get_current_environmental_data() -> dict:
    weather    = get_weather_by_location(28.61, 77.23)
    rainfall   = weather["rainfall"]
    wind_speed = weather["wind_speed"]
    aqi        = 200.0
    return _build_env_payload(rainfall, aqi, wind_speed, "Live Weather API")


def get_simulated_event() -> dict:
    roll = random.random()
    if roll < 0.60:
        s = random.choice(_DISRUPTION_SCENARIOS)
    elif roll < 0.80:
        s = random.choice(_MEDIUM_SCENARIOS)
    else:
        s = random.choice(_CALM_SCENARIOS)
    return _build_env_payload(s["rainfall"], s["aqi"], s["wind_speed"], s["label"])


def get_dashboard_data() -> dict:
    env = get_current_environmental_data()
    return {
        "worker": WORKER_PROFILE,
        "plan":   COVERAGE_PLAN,
        "current_risk": {
            "risk_score":           env["risk_score"],
            "risk_level":           env["risk_level"],
            "primary_hazard":       env["primary_hazard"],
            "rainfall":             env["rainfall"],
            "aqi":                  env["aqi"],
            "wind_speed":           env["wind_speed"],
            "imd_bands":            env["imd_bands"],
            "confidence":           env["confidence"],
            "risk_trend":           env["risk_trend"],
            # v4 NEW
            "trend":                env["trend"],
            "trend_velocity":       env["trend_velocity"],
            "anomaly_flag":         env["anomaly_flag"],
            "anomaly_severity":     env["anomaly_severity"],
            "predicted_risk_score": env["predicted_risk_score"],
            "predicted_risk_level": env["predicted_risk_level"],
            "risk_category_reason": env["risk_category_reason"],
            "decision_explanation": env["decision_explanation"],
        },
        "payout_status": {
            "triggered":           env["payout_triggered"],
            "tier_label":          env["tier_label"],
            "payout_percentage":   env["payout_percentage"],
            "gross_payout":        env["gross_payout"],
            "platform_fee":        env["platform_fee"],
            "net_payout":          env["net_payout"],
            "risk_loading":        env["risk_loading"],
            "claim_adjustment":    env["claim_adjustment"],
            "final_payout":        env["final_payout"],
            "effective_payout":    env["effective_payout"],
            "amount_inr":          env["effective_payout"],
            "exclusion":           env["exclusion"],
            "fraud_check":         env["fraud_check"],
            "message":             env["payout_message"],
            "payout_explanation":  env["payout_explanation"],
            "delivery":            PAYOUT_DELIVERY,
        },
        "actuarial":    env["actuarial"],
        "last_updated": env["timestamp"],
    }
