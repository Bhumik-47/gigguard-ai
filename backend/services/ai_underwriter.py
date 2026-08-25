import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Fallback rule-based scoring if Gemini is unavailable or returns malformed JSON
def _rule_based_risk_score(worker_profile: dict, weather_context: dict) -> dict:
    rainfall = weather_context.get("rainfall_mm_per_hr", 0)
    wind = weather_context.get("wind_speed_kmh", 0)
    temp = weather_context.get("temperature_celsius", 25)
    aqi = weather_context.get("aqi_pm25", 50)

    score = 0
    factors = []

    if rainfall > 15:
        score += 40
        factors.append(f"Heavy rainfall: {rainfall} mm/hr")
    elif rainfall > 5:
        score += 20
        factors.append(f"Moderate rainfall: {rainfall} mm/hr")

    if wind > 40:
        score += 25
        factors.append(f"High wind speed: {wind} km/h")

    if aqi > 150:
        score += 25
        factors.append(f"Hazardous AQI: {aqi}")
    elif aqi > 100:
        score += 15
        factors.append(f"Unhealthy AQI: {aqi}")

    if temp > 40:
        score += 10
        factors.append(f"Extreme heat: {temp}°C")

    score = min(score, 100)

    if score < 30:
        category = "low"
        premium = 2.0
    elif score < 60:
        category = "moderate"
        premium = 5.0
    elif score < 80:
        category = "high"
        premium = 10.0
    else:
        category = "extreme"
        premium = 18.0

    return {
        "risk_score": score,
        "risk_category": category,
        "recommended_premium_inr": premium,
        "risk_factors": factors if factors else ["Conditions are within safe limits"],
        "coverage_recommendation": f"{category.capitalize()} risk level detected. "
                                   f"{'Extended coverage recommended.' if score > 60 else 'Standard coverage sufficient.'}",
        "source": "rule_based_fallback",
    }


def generate_risk_assessment(
    worker_profile: dict,
    weather_context: dict,
    aqi_context: Optional[dict] = None,
) -> dict:
    """
    Uses Gemini to generate a structured risk score and recommended premium.
    Falls back to rule-based scoring if Gemini is unavailable or returns bad JSON.
    
    Args:
        worker_profile: dict with keys: vehicle_type, city, shift_hours, claim_history
        weather_context: dict with keys: temperature_celsius, rainfall_mm_per_hr, wind_speed_kmh
        aqi_context: optional dict with key: aqi_pm25
    
    Returns:
        dict with: risk_score, risk_category, recommended_premium_inr, 
                   risk_factors, coverage_recommendation
    """
    if aqi_context is None:
        aqi_context = {}

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — using rule-based fallback")
        return _rule_based_risk_score(worker_profile, {**weather_context, **aqi_context})

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
You are an AI underwriting engine for a parametric insurance platform protecting gig economy workers in India.

Analyze the following inputs and return a JSON object with EXACTLY these keys:
- risk_score: integer from 0-100 (higher = more risk)
- risk_category: one of ["low", "moderate", "high", "extreme"]
- recommended_premium_inr: float (micro-premium per shift hour, in INR)
- risk_factors: list of strings explaining the key risk drivers
- coverage_recommendation: string describing what coverage is most appropriate

Worker Profile:
- Vehicle Type: {worker_profile.get('vehicle_type', 'motorbike')}
- City/Zone: {worker_profile.get('city', 'Unknown')}
- Shift Duration: {worker_profile.get('shift_hours', 8)} hours
- Historical Claim Count: {worker_profile.get('claim_history', 0)}

Current Environmental Conditions:
- Temperature: {weather_context.get('temperature_celsius', 'N/A')}°C
- Rainfall: {weather_context.get('rainfall_mm_per_hr', 0)} mm/hr
- Wind Speed: {weather_context.get('wind_speed_kmh', 0)} km/h
- AQI (PM2.5): {aqi_context.get('aqi_pm25', 'unavailable')}

Return ONLY valid JSON. No markdown, no explanation, no code fences.
"""

        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)

        # Validate expected keys exist
        required_keys = {
            "risk_score", "risk_category",
            "recommended_premium_inr", "risk_factors",
            "coverage_recommendation",
        }
        if not required_keys.issubset(result.keys()):
            raise ValueError(f"Gemini response missing keys: {required_keys - result.keys()}")

        result["source"] = "gemini"
        return result

    except Exception as e:
        logger.error(f"Gemini AI underwriting failed: {e} — using rule-based fallback")
        return _rule_based_risk_score(worker_profile, {**weather_context, **aqi_context})