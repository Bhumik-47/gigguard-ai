# backend/tests/test_environment_status.py
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


MOCK_WEATHER_RESPONSE = {
    "main": {"temp": 32.5, "humidity": 78},
    "wind": {"speed": 3.2},
    "rain": {"1h": 2.0},
    "weather": [{"description": "moderate rain"}],
}

MOCK_AQI_RESPONSE = {
    "list": [{"main": {"aqi": 2}}]
}


def test_environment_status_normal_conditions(monkeypatch):
    """Normal conditions — no threshold breach."""
    with patch("routes.environment.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        weather_mock = AsyncMock()
        weather_mock.raise_for_status = AsyncMock()
        weather_mock.json.return_value = MOCK_WEATHER_RESPONSE

        aqi_mock = AsyncMock()
        aqi_mock.raise_for_status = AsyncMock()
        aqi_mock.json.return_value = MOCK_AQI_RESPONSE

        mock_client.get.side_effect = [weather_mock, aqi_mock]

        import os
        monkeypatch.setenv("OPENWEATHER_API_KEY", "test_key")

        res = client.get("/api/environment/status?lat=12.97&lon=77.59&policy_id=POL-001")
        assert res.status_code == 200
        data = res.json()
        assert data["threshold_breached"] is False
        assert data["temperature_celsius"] == 32.5
        assert data["policy_id"] == "POL-001"


def test_environment_status_missing_api_key():
    """Should return 503 when API key is not set."""
    import os
    os.environ.pop("OPENWEATHER_API_KEY", None)
    res = client.get("/api/environment/status?lat=12.97&lon=77.59")
    assert res.status_code == 503
    assert "OPENWEATHER_API_KEY" in res.json()["detail"]


def test_environment_status_invalid_lat():
    """Out-of-range latitude should return 422."""
    res = client.get("/api/environment/status?lat=200&lon=77.59")
    assert res.status_code == 422