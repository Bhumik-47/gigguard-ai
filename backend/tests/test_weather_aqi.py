"""
Unit tests for weather_service, aqi_service, and trigger_evaluator.
Uses pytest-mock to avoid making real HTTP calls during CI.
"""
import pytest
from unittest.mock import patch, MagicMock

from services.weather_service import get_weather_data
from services.aqi_service import get_aqi_data
from services.trigger_evaluator import evaluate_trigger


# --- weather_service tests ---

MOCK_WEATHER_RESPONSE = {
    "main": {"temp": 38.5},
    "rain": {"1h": 5.2},
    "wind": {"speed": 8.0},
    "weather": [{"description": "heavy rain"}],
    "name": "Mumbai",
    "dt": 1720000000,
}


@patch("services.weather_service.requests.get")
@patch.dict("os.environ", {"OPENWEATHERMAP_API_KEY": "test_key"})
def test_get_weather_data_success(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = MOCK_WEATHER_RESPONSE
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    result = get_weather_data(19.07, 72.87)

    assert result["temperature_celsius"] == 38.5
    assert result["rainfall_mm_per_hr"] == 5.2
    assert result["wind_speed_kmh"] == pytest.approx(28.8, rel=0.01)
    assert result["city"] == "Mumbai"


@patch("services.weather_service.requests.get")
@patch.dict("os.environ", {"OPENWEATHERMAP_API_KEY": "test_key"})
def test_get_weather_data_no_rain(mock_get):
    response_no_rain = {**MOCK_WEATHER_RESPONSE}
    response_no_rain.pop("rain", None)

    mock_response = MagicMock()
    mock_response.json.return_value = response_no_rain
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    result = get_weather_data(19.07, 72.87)
    assert result["rainfall_mm_per_hr"] == 0.0


def test_get_weather_data_missing_key():
    import os
    os.environ.pop("OPENWEATHERMAP_API_KEY", None)
    # Re-import to pick up env change
    import importlib
    import services.weather_service as ws
    importlib.reload(ws)
    ws.OPENWEATHER_API_KEY = None

    with pytest.raises(ValueError, match="OPENWEATHERMAP_API_KEY"):
        ws.get_weather_data(19.07, 72.87)


# --- aqi_service tests ---

MOCK_AQI_RESPONSE = {
    "results": [
        {
            "name": "Andheri Station",
            "measurements": [
                {"value": 180.5, "unit": "µg/m³", "lastUpdated": "2024-07-01T10:00:00Z"}
            ],
        }
    ]
}


@patch("services.aqi_service.requests.get")
def test_get_aqi_data_success(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = MOCK_AQI_RESPONSE
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    result = get_aqi_data(19.07, 72.87)
    assert result["aqi_pm25"] == 180.5
    assert result["location"] == "Andheri Station"


@patch("services.aqi_service.requests.get")
def test_get_aqi_data_no_station(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    result = get_aqi_data(19.07, 72.87)
    assert result["aqi_pm25"] is None
    assert result["source"] == "no_station_found"


# --- trigger_evaluator tests ---

def test_evaluate_trigger_all_clear():
    weather = {"temperature_celsius": 30.0, "rainfall_mm_per_hr": 2.0}
    aqi = {"aqi_pm25": 50.0}
    policy = {
        "covers_heat": True, "heat_threshold_celsius": 45,
        "covers_rain": True, "rain_threshold_mm": 30,
        "covers_aqi": True, "aqi_threshold": 250,
    }
    triggered, reasons = evaluate_trigger(weather, aqi, policy)
    assert triggered is False
    assert reasons == []


def test_evaluate_trigger_extreme_heat():
    weather = {"temperature_celsius": 47.0, "rainfall_mm_per_hr": 0.0}
    aqi = {"aqi_pm25": 100.0}
    policy = {"covers_heat": True, "heat_threshold_celsius": 45}
    triggered, reasons = evaluate_trigger(weather, aqi, policy)
    assert triggered is True
    assert "extreme_heat" in reasons


def test_evaluate_trigger_multiple():
    weather = {"temperature_celsius": 46.0, "rainfall_mm_per_hr": 35.0}
    aqi = {"aqi_pm25": 300.0}
    policy = {
        "covers_heat": True, "heat_threshold_celsius": 45,
        "covers_rain": True, "rain_threshold_mm": 30,
        "covers_aqi": True, "aqi_threshold": 250,
    }
    triggered, reasons = evaluate_trigger(weather, aqi, policy)
    assert triggered is True
    assert len(reasons) == 3