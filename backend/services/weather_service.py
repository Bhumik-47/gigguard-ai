import os
import requests
from requests.exceptions import HTTPError, Timeout, RequestException

OPENWEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather_data(lat: float, lon: float) -> dict:
    """
    Fetch current weather metrics for given coordinates.
    Returns a normalized dict of weather fields used by the risk engine.
    Raises ValueError if the API key is not configured.
    Raises RuntimeError on HTTP or network errors.
    """
    if not OPENWEATHER_API_KEY:
        raise ValueError(
            "OPENWEATHERMAP_API_KEY is not set. "
            "Add it to your .env file and restart the server."
        )

    try:
        response = requests.get(
            BASE_URL,
            params={
                "lat": lat,
                "lon": lon,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
            },
            timeout=10,
        )
        response.raise_for_status()
    except HTTPError as e:
        raise RuntimeError(f"OpenWeatherMap API error: {e}") from e
    except Timeout:
        raise RuntimeError("OpenWeatherMap API timed out after 10 seconds.")
    except RequestException as e:
        raise RuntimeError(f"Network error calling OpenWeatherMap: {e}") from e

    data = response.json()
    return {
        "temperature_celsius": data["main"]["temp"],
        "rainfall_mm_per_hr": data.get("rain", {}).get("1h", 0.0),
        "wind_speed_kmh": round(data["wind"]["speed"] * 3.6, 2),
        "description": data["weather"][0]["description"],
        "city": data["name"],
        "timestamp": data["dt"],
    }