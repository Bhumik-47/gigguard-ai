"""
data_service.py
---------------
GigGuard AI — Data Service

Provides two categories of data:

1. Static mock data  — worker profile, active plan, platform info.
   In production these would be fetched from a database (PostgreSQL,
   DynamoDB, etc.) and third-party data providers.

2. Live / simulated environmental data  — returns either a realistic
   "disruption scenario" or a calm baseline, chosen randomly to simulate
   real API responses from IMD / CPCB / SAFAR weather feeds.

All public functions return plain Python dicts so they can be serialised
directly to JSON by FastAPI's response models.
"""

import random
from datetime import datetime, date

from risk_engine import calculate_risk, RiskResult
from payout_engine import calculate_payout, CoveragePlan, PayoutResult


# ---------------------------------------------------------------------------
# Static worker & plan data
# (Replace with DB queries in production)
# ---------------------------------------------------------------------------

WORKER_PROFILE = {
    "id": "SWG-09124",
    "name": "Ravi Kumar",
    "platform": "Swiggy",
    "zone": "Delhi NCR — Laxmi Nagar",
    "status": "Active",
    "shift_started": "09:30 AM",
    "days_covered": 47,
    "member_since": "Jan 2025",
}

COVERAGE_PLAN = {
    "plan_name": "Weekly Shield",
    "plan_type": "Parametric Weather Insurance",
    "premium_inr": 49,
    "premium_period": "week",
    "coverage_cap_inr": 2500,
    "max_claims_per_week": 2,
    "claims_used_this_week": 1,
    "valid_until": str(date(2026, 3, 16)),
    "claim_process": "Fully Automatic",
    "triggers": {
        "rainfall_mm_per_hr": 50,
        "aqi_ug_m3": 250,
        "wind_speed_km_h": 45,
    },
}

PAYOUT_DELIVERY = {
    "method": "UPI Auto-Transfer",
    "upi_id_masked": "rkumar**91@upi",
    "eta_hours": 2,
}


# ---------------------------------------------------------------------------
# Environmental scenario library
# Rotated randomly so repeated /simulate calls feel dynamic.
# ---------------------------------------------------------------------------

# Disruption scenarios (risk will be HIGH / CRITICAL → payout triggered)
_DISRUPTION_SCENARIOS = [
    {"rainfall": 87.0, "aqi": 312.0, "wind_speed": 54.0, "label": "Heavy monsoon + smog"},
    {"rainfall": 95.0, "aqi": 280.0, "wind_speed": 60.0, "label": "Cyclonic rainfall"},
    {"rainfall": 55.0, "aqi": 390.0, "wind_speed": 47.0, "label": "Industrial smog + rain"},
    {"rainfall": 70.0, "aqi": 340.0, "wind_speed": 65.0, "label": "Thunderstorm"},
    {"rainfall": 110.0,"aqi": 200.0, "wind_speed": 70.0, "label": "Extreme rainfall event"},
]

# Calm scenarios (risk LOW → no payout)
_CALM_SCENARIOS = [
    {"rainfall": 5.0,  "aqi": 80.0,  "wind_speed": 12.0, "label": "Clear morning"},
    {"rainfall": 0.0,  "aqi": 95.0,  "wind_speed": 18.0, "label": "Sunny & breezy"},
    {"rainfall": 8.0,  "aqi": 70.0,  "wind_speed": 10.0, "label": "Light drizzle"},
]

# Medium scenarios (risk MEDIUM → no payout, close to threshold)
_MEDIUM_SCENARIOS = [
    {"rainfall": 35.0, "aqi": 200.0, "wind_speed": 35.0, "label": "Moderate pollution"},
    {"rainfall": 45.0, "aqi": 230.0, "wind_speed": 40.0, "label": "Pre-monsoon haze"},
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _current_timestamp() -> str:
    """Return a formatted current timestamp string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _build_env_payload(
    rainfall: float,
    aqi: float,
    wind_speed: float,
    label: str = "",
) -> dict:
    """
    Run both engines and bundle results into a single response dict.
    This is the shared building block for /risk and /simulate.
    """
    # Risk engine
    risk: RiskResult = calculate_risk(rainfall, aqi, wind_speed)

    # Payout engine
    plan = CoveragePlan(
        plan_name=COVERAGE_PLAN["plan_name"],
        coverage_cap=COVERAGE_PLAN["coverage_cap_inr"],
        premium=COVERAGE_PLAN["premium_inr"],
    )
    payout: PayoutResult = calculate_payout(risk.risk_score, risk.risk_level, plan)

    return {
        # Raw environmental readings
        "rainfall": rainfall,
        "aqi": aqi,
        "wind_speed": wind_speed,
        "scenario_label": label,

        # Risk engine outputs
        "component_scores": {
            "rainfall_score": risk.rainfall_score,
            "aqi_score": risk.aqi_score,
            "wind_score": risk.wind_score,
        },
        "risk_score": risk.risk_score,
        "risk_level": risk.risk_level,

        # Payout engine outputs
        "payout_triggered": payout.payout_triggered,
        "payout_percentage": payout.payout_percentage,
        "gross_payout": payout.gross_payout,
        "platform_fee": payout.platform_fee,
        "payout": payout.net_payout,            # top-level for simple consumers
        "payout_message": payout.message,

        "timestamp": _current_timestamp(),
    }


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def get_current_environmental_data() -> dict:
    """
    Return the current environmental readings.
    For the hackathon we use the "active disruption" scenario to make the
    demo compelling.  Swap this with a real IMD/CPCB API call in production.
    """
    # Always use the first disruption scenario as the "live" reading
    s = _DISRUPTION_SCENARIOS[0]
    return _build_env_payload(s["rainfall"], s["aqi"], s["wind_speed"], s["label"])


def get_simulated_event() -> dict:
    """
    Return a randomly chosen scenario (weighted 60 % disruption, 20 % medium,
    20 % calm) to make repeated /simulate calls feel dynamic.
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
    Aggregate all data needed for the Worker Dashboard page.
    Combines worker profile, plan, and the latest risk/payout snapshot.
    """
    env = get_current_environmental_data()

    return {
        # Worker info
        "worker": WORKER_PROFILE,

        # Insurance plan
        "plan": COVERAGE_PLAN,

        # Live risk snapshot
        "current_risk": {
            "risk_score": env["risk_score"],
            "risk_level": env["risk_level"],
            "rainfall": env["rainfall"],
            "aqi": env["aqi"],
            "wind_speed": env["wind_speed"],
        },

        # Payout status
        "payout_status": {
            "triggered": env["payout_triggered"],
            "amount_inr": env["payout"],
            "payout_percentage": env["payout_percentage"],
            "message": env["payout_message"],
            "delivery": PAYOUT_DELIVERY,
        },

        "last_updated": env["timestamp"],
    }
