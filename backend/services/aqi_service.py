import requests
from requests.exceptions import HTTPError, Timeout, RequestException

OPENAQ_BASE_URL = "https://api.openaq.io/v2/latest"


def get_aqi_data(lat: float, lon: float, radius_meters: int = 10000) -> dict:
    """
    Fetch latest PM2.5 AQI reading near given coordinates via OpenAQ.
    Returns a normalized dict. Returns aqi_pm25=None if no station is nearby.
    OpenAQ v2 /latest is free and requires no API key for basic usage.
    """
    try:
        response = requests.get(
            OPENAQ_BASE_URL,
            params={
                "coordinates": f"{lat},{lon}",
                "radius": radius_meters,
                "limit": 1,
                "parameter": "pm25",
            },
            timeout=10,
        )
        response.raise_for_status()
    except HTTPError as e:
        raise RuntimeError(f"OpenAQ API error: {e}") from e
    except Timeout:
        raise RuntimeError("OpenAQ API timed out after 10 seconds.")
    except RequestException as e:
        raise RuntimeError(f"Network error calling OpenAQ: {e}") from e

    results = response.json().get("results", [])
    if not results or not results[0].get("measurements"):
        return {"aqi_pm25": None, "source": "no_station_found"}

    measurement = results[0]["measurements"][0]
    return {
        "aqi_pm25": measurement["value"],
        "unit": measurement["unit"],
        "location": results[0]["name"],
        "timestamp": measurement["lastUpdated"],
    }