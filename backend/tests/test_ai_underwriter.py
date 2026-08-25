import pytest
from unittest.mock import patch, MagicMock
from backend.services.ai_underwriter import generate_risk_assessment, _rule_based_risk_score

SAMPLE_WORKER = {
    "vehicle_type": "motorbike",
    "city": "Bengaluru",
    "shift_hours": 8,
    "claim_history": 0,
}

SAMPLE_WEATHER = {
    "temperature_celsius": 35,
    "rainfall_mm_per_hr": 20,
    "wind_speed_kmh": 50,
}

SAMPLE_AQI = {"aqi_pm25": 160}


def test_rule_based_fallback_high_rain():
    result = _rule_based_risk_score(SAMPLE_WORKER, SAMPLE_WEATHER)
    assert result["risk_score"] >= 50
    assert result["risk_category"] in ["moderate", "high", "extreme"]
    assert isinstance(result["risk_factors"], list)
    assert result["source"] == "rule_based_fallback"


def test_rule_based_fallback_safe_conditions():
    safe_weather = {"temperature_celsius": 25, "rainfall_mm_per_hr": 0, "wind_speed_kmh": 10}
    result = _rule_based_risk_score(SAMPLE_WORKER, safe_weather)
    assert result["risk_score"] < 30
    assert result["risk_category"] == "low"


def test_gemini_success():
    mock_response_text = '{"risk_score": 75, "risk_category": "high", "recommended_premium_inr": 10.5, "risk_factors": ["Heavy rain", "High wind"], "coverage_recommendation": "Extended coverage recommended."}'

    with patch("os.getenv", return_value="fake_key"), \
         patch("google.generativeai.configure"), \
         patch("google.generativeai.GenerativeModel") as MockModel:
        
        mock_instance = MockModel.return_value
        mock_instance.generate_content.return_value = MagicMock(text=mock_response_text)

        result = generate_risk_assessment(SAMPLE_WORKER, SAMPLE_WEATHER, SAMPLE_AQI)
        assert result["risk_score"] == 75
        assert result["source"] == "gemini"


def test_gemini_malformed_json_triggers_fallback():
    with patch("os.getenv", return_value="fake_key"), \
         patch("google.generativeai.configure"), \
         patch("google.generativeai.GenerativeModel") as MockModel:

        mock_instance = MockModel.return_value
        mock_instance.generate_content.return_value = MagicMock(text="NOT_VALID_JSON")

        result = generate_risk_assessment(SAMPLE_WORKER, SAMPLE_WEATHER, SAMPLE_AQI)
        assert result["source"] == "rule_based_fallback"


def test_no_api_key_triggers_fallback():
    with patch("os.getenv", return_value=None):
        result = generate_risk_assessment(SAMPLE_WORKER, SAMPLE_WEATHER, SAMPLE_AQI)
        assert result["source"] == "rule_based_fallback"