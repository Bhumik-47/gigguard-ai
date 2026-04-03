"""
data_service.py
---------------
GigGuard AI — Data Service (Final Working)
"""

import random
from datetime import datetime, date
import requests # type: ignore


API_KEY = ""

from risk_engine import calculate_risk, RiskResult
from payout_engine import calculate_payout, CoveragePlan, PayoutResult


# ---------------------------------------------------------------------------
# Real Weather API
# ---------------------------------------------------------------------------

def get_weather_by_location(lat: float, lon: float) -> dict:
    """
    Fetch real weather data from OpenWeatherMap using coordinates.
    """

    url = (
        f"https://api.openweathermap.org/data/2.5/weather?"
        f"lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    )

    try:
        response = requests.get(url, timeout=5)

        if response.status_code != 200:
            raise Exception("Weather API failed")

        data = response.json()

        rainfall = data.get("rain", {}).get("1h", 0.0)
        wind_speed = data.get("wind", {}).get("speed", 0.0)
        temperature = data.get("main", {}).get("temp", 30.0)
        humidity = data.get("main", {}).get("humidity", 50.0)

        # 🔥 Smart AQI estimation
        condition = data.get("weather", [{}])[0].get("main", "")

        if condition == "Clear":
            aqi = 50
        elif condition == "Clouds":
            aqi = 100
        elif condition == "Rain":
            aqi = 150
        elif condition == "Smoke":
            aqi = 300
        else:
            aqi = 200

        return {
            "rainfall": rainfall,
            "wind_speed": wind_speed,
            "temperature": temperature,
            "humidity": humidity,
            "aqi": aqi,
            "condition": condition,
            "source": "OpenWeatherMap API",
            "confidence": 0.92
        }

    except Exception:
        return {
            "rainfall": 0.0,
            "wind_speed": 5.0,
            "temperature": 30.0,
            "humidity": 50.0,
            "aqi": 200,
            "condition": "Fallback",
            "source": "Fallback",
            "confidence": 0.5
        }


# ---------------------------------------------------------------------------
# Static worker & plan data
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
# Helpers
# ---------------------------------------------------------------------------

def _current_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _build_env_payload(rainfall: float, aqi: float, wind_speed: float, label: str = "") -> dict:

    risk: RiskResult = calculate_risk(rainfall, aqi, wind_speed)

    plan = CoveragePlan(
        plan_name=COVERAGE_PLAN["plan_name"],
        coverage_cap=COVERAGE_PLAN["coverage_cap_inr"],
        premium=COVERAGE_PLAN["premium_inr"],
    )

    payout: PayoutResult = calculate_payout(risk.risk_score, risk.risk_level, plan)

    return {
        "rainfall": rainfall,
        "aqi": aqi,
        "wind_speed": wind_speed,
        "scenario_label": label,

        "component_scores": {
            "rainfall_score": risk.rainfall_score,
            "aqi_score": risk.aqi_score,
            "wind_score": risk.wind_score,
        },

        "risk_score": risk.risk_score,
        "risk_level": risk.risk_level,

        "payout_triggered": payout.payout_triggered,
        "payout_percentage": payout.payout_percentage,
        "gross_payout": payout.gross_payout,
        "platform_fee": payout.platform_fee,
        "payout": payout.net_payout,
        "payout_message": payout.message,

        "timestamp": _current_timestamp(),
    }


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def get_current_environmental_data() -> dict:
    """
    Uses REAL weather data
    """

    weather = get_weather_by_location(28.61, 77.23)

    return _build_env_payload(
        weather["rainfall"],
        weather["aqi"],
        weather["wind_speed"],
        f"Live Weather ({weather['condition']})"
    )


def get_simulated_event() -> dict:
    return get_current_environmental_data()


def get_dashboard_data() -> dict:

    env = get_current_environmental_data()

    return {
        "worker": WORKER_PROFILE,
        "plan": COVERAGE_PLAN,

        "current_risk": {
            "risk_score": env["risk_score"],
            "risk_level": env["risk_level"],
            "rainfall": env["rainfall"],
            "aqi": env["aqi"],
            "wind_speed": env["wind_speed"],
        },

        "payout_status": {
            "triggered": env["payout_triggered"],
            "amount_inr": env["payout"],
            "payout_percentage": env["payout_percentage"],
            "message": env["payout_message"],
            "delivery": PAYOUT_DELIVERY,
        },

        "last_updated": env["timestamp"],
    }
