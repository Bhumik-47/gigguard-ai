"""
data_service.py
---------------
GigGuard AI — Data Service  (v3)

Orchestrates all four engines in the correct order:
  1. risk_engine   → calculate_risk(), predict_risk_trend()
  2. exclusions    → evaluate_exclusions()        (BEFORE payout — no point
                     computing amounts for excluded claims)
  3. payout_engine → calculate_payout() + apply_exclusion_to_payout()
  4. fraud_engine  → detect_fraud()              (AFTER payout decision —
                     needs to see whether payout was triggered)

All v1 public function signatures are preserved unchanged:
  get_weather_by_location()
  get_current_environmental_data()
  get_simulated_event()
  get_dashboard_data()
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
# Static worker & plan data (unchanged from v1)
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
    # v3 NEW — explicit exclusion summary displayed on frontend plan card
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

# Default claim context — in production, fetched from DB per worker
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
# Environmental scenario library (expanded from v1)
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
    {"rainfall": 5.0, "aqi": 80.0, "wind_speed": 12.0, "label": "Clear morning"},
    {"rainfall": 0.0, "aqi": 60.0, "wind_speed": 8.0,  "label": "Sunny day"},
]


# ---------------------------------------------------------------------------
# Real weather API (unchanged from v1)
# ---------------------------------------------------------------------------

def get_weather_by_location(lat: float, lon: float) -> dict:
    """
    Fetch real weather data from OpenWeatherMap using coordinates.
    Falls back to safe defaults if the API is unreachable.
    """
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
# Core payload builder — orchestrates all 4 engines
# ---------------------------------------------------------------------------

def _build_env_payload(
    rainfall:   float,
    aqi:        float,
    wind_speed: float,
    label:      str = "",
    claim_ctx:  ClaimContext = _DEFAULT_CLAIM_CTX,
) -> dict:
    """
    Run all engines in sequence and assemble a single structured response dict.

    Engine order (important)
    ------------------------
    1. Risk engine   — pure environmental scoring; no business logic
    2. Exclusion engine — check BEFORE payout (exclude first, compute second)
    3. Payout engine — compute amounts; apply exclusion adjustment
    4. Fraud engine  — check AFTER payout decision (needs trigger result)
    5. Zero out effective_payout if fraud verdict is SUSPICIOUS or BLOCKED
    """

    # ── 1. Risk engine ────────────────────────────────────────────────────
    risk:  RiskResult  = calculate_risk(rainfall, aqi, wind_speed)
    trend: TrendResult = predict_risk_trend(rainfall, aqi, wind_speed)

    # ── 2. Exclusion engine ───────────────────────────────────────────────
    exclusion: ExclusionResult = evaluate_exclusions(claim_ctx)

    # ── 3. Payout engine ──────────────────────────────────────────────────
    plan = CoveragePlan(
        plan_name=           COVERAGE_PLAN["plan_name"],
        coverage_cap=        COVERAGE_PLAN["coverage_cap_inr"],
        premium=             COVERAGE_PLAN["premium_inr"],
        max_claims_per_week= COVERAGE_PLAN["max_claims_per_week"],
        max_claims_per_month=COVERAGE_PLAN["max_claims_per_month"],
    )
    payout: PayoutResult = calculate_payout(
        risk.risk_score, risk.risk_level, plan, include_actuarial=True
    )

    # Apply exclusion adjustment to payout amounts
    if exclusion.is_excluded:
        payout = apply_exclusion_to_payout(
            payout,
            exclusion_code=   exclusion.exclusion_code,
            is_partial=       exclusion.is_partial,
            reduction_pct=    exclusion.reduction_pct,
            exclusion_reason= exclusion.reason,
        )

    # Effective payout = exclusion-adjusted amount (or full net if SAFE)
    effective = payout.adjusted_net_payout if exclusion.is_excluded else payout.net_payout

    # ── 4. Fraud engine ───────────────────────────────────────────────────
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
    )

    # ── 5. Zero out payout if fraud verdict is SUSPICIOUS or BLOCKED ──────
    if fraud.verdict in ("BLOCKED", "SUSPICIOUS"):
        effective = 0.0

    # ── Assemble response ─────────────────────────────────────────────────
    act = payout.actuarial

    return {
        # Raw readings
        "rainfall":       rainfall,
        "aqi":            aqi,
        "wind_speed":     wind_speed,
        "scenario_label": label,

        # Risk engine
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

        # Trend prediction
        "risk_trend": {
            "trend":                trend.trend,
            "message":              trend.message,
            "eta_hours":            trend.eta_hours,
            "contributing_factors": trend.contributing_factors,
            "confidence":           trend.confidence,
        },

        # Exclusion engine
        "exclusion": {
            "is_excluded":        exclusion.is_excluded,
            "exclusion_code":     exclusion.exclusion_code,
            "reason":             exclusion.reason,
            "is_partial":         exclusion.is_partial,
            "reduction_pct":      exclusion.reduction_pct,
            "applicable_clauses": exclusion.applicable_clauses,
        },

        # Payout engine — full financial breakdown
        "payout_triggered":    payout.payout_triggered,
        "tier_label":          payout.tier_label,
        "tier_desc":           payout.tier_desc,
        "payout_percentage":   payout.payout_percentage,
        "coverage_cap":        payout.coverage_cap,
        "gross_payout":        payout.gross_payout,
        "platform_fee":        payout.platform_fee,
        "net_payout":          payout.net_payout,
        "effective_payout":    effective,       # post-exclusion + post-fraud
        "payout":              effective,       # v1 compatibility alias
        "payout_message":      payout.message,
        "exclusion_applied":   payout.exclusion_applied,
        "adjusted_net_payout": payout.adjusted_net_payout,

        # Actuarial model
        "actuarial": {
            "pure_premium":          act.pure_premium           if act else None,
            "loaded_premium":        act.loaded_premium         if act else None,
            "premium_adequacy":      act.premium_adequacy       if act else None,
            "expected_loss_ratio":   act.expected_loss_ratio    if act else None,
            "claims_reserve":        act.claims_reserve         if act else None,
            "expected_weekly_payout":act.expected_weekly_payout if act else None,
        },

        # Fraud detection
        "fraud_check": {
            "fraud_score":  fraud.fraud_score,
            "verdict":      fraud.verdict,      # SAFE | REVIEW | SUSPICIOUS | BLOCKED
            "flag_codes":   fraud.flag_codes,
            "reason":       fraud.reason,
            "auto_approve": fraud.auto_approve,
            "flags": [
                {
                    "rule_code":   f.rule_code,
                    "weight":      f.weight,
                    "description": f.description,
                }
                for f in fraud.flags
            ],
        },

        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ---------------------------------------------------------------------------
# Public service functions — all v1 signatures preserved
# ---------------------------------------------------------------------------

def get_current_environmental_data() -> dict:
    """
    Fetch live weather from OpenWeatherMap and run the full engine pipeline.
    AQI is a static placeholder (200 µg/m³) until a CPCB/SAFAR API key
    is configured. Swap with a real AQI endpoint in production.
    """
    weather    = get_weather_by_location(28.61, 77.23)   # Delhi, India
    rainfall   = weather["rainfall"]
    wind_speed = weather["wind_speed"]
    aqi        = 200.0   # placeholder

    return _build_env_payload(rainfall, aqi, wind_speed, "Live Weather API")


def get_simulated_event() -> dict:
    """
    Return a randomly chosen scenario.
    Weighted: 60% disruption / 20% medium / 20% calm.
    Repeated calls demonstrate the full range of all engines.
    """
    roll = random.random()
    if roll < 0.60:
        s = random.choice(_DISRUPTION_SCENARIOS)
    elif roll < 0.80:
        s = random.choice(_MEDIUM_SCENARIOS)
    else:
        s = random.choice(_CALM_SCENARIOS)
    return _build_env_payload(s["rainfall"], s["aqi"], s["wind_speed"], s["label"])


def get_dashboard_data() -> dict:
    """
    Aggregate all data for the Worker Dashboard page (dashboard.html).
    Runs the full engine pipeline and structures the result for the UI.
    """
    env = get_current_environmental_data()

    return {
        "worker": WORKER_PROFILE,
        "plan":   COVERAGE_PLAN,

        # Risk snapshot — includes trend + confidence
        "current_risk": {
            "risk_score":     env["risk_score"],
            "risk_level":     env["risk_level"],
            "primary_hazard": env["primary_hazard"],
            "rainfall":       env["rainfall"],
            "aqi":            env["aqi"],
            "wind_speed":     env["wind_speed"],
            "imd_bands":      env["imd_bands"],
            "confidence":     env["confidence"],
            "risk_trend":     env["risk_trend"],
        },

        # Payout status — full breakdown + exclusion + fraud
        "payout_status": {
            "triggered":          env["payout_triggered"],
            "tier_label":         env["tier_label"],
            "payout_percentage":  env["payout_percentage"],
            "gross_payout":       env["gross_payout"],
            "platform_fee":       env["platform_fee"],
            "net_payout":         env["net_payout"],
            "effective_payout":   env["effective_payout"],
            "amount_inr":         env["effective_payout"],   # v1 compat
            "exclusion":          env["exclusion"],
            "fraud_check":        env["fraud_check"],
            "message":            env["payout_message"],
            "delivery":           PAYOUT_DELIVERY,
        },

        "actuarial":    env["actuarial"],
        "last_updated": env["timestamp"],
    }
