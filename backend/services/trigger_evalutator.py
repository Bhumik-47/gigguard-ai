from typing import Tuple, List


def evaluate_trigger(
    weather: dict, aqi: dict, policy: dict
) -> Tuple[bool, List[str]]:
    """
    Determines if parametric trigger conditions are met for a given policy.

    Args:
        weather: Output from weather_service.get_weather_data()
        aqi:     Output from aqi_service.get_aqi_data()
        policy:  Dict with boolean flags and numeric thresholds, e.g.:
                 {
                   "covers_heat": True,
                   "heat_threshold_celsius": 45,
                   "covers_rain": True,
                   "rain_threshold_mm": 30,
                   "covers_aqi": True,
                   "aqi_threshold": 250,
                 }

    Returns:
        (triggered: bool, triggers_met: List[str])
    """
    triggers_met: List[str] = []

    if (
        policy.get("covers_heat")
        and weather.get("temperature_celsius") is not None
        and weather["temperature_celsius"] >= policy.get("heat_threshold_celsius", 45)
    ):
        triggers_met.append("extreme_heat")

    if (
        policy.get("covers_rain")
        and weather.get("rainfall_mm_per_hr") is not None
        and weather["rainfall_mm_per_hr"] >= policy.get("rain_threshold_mm", 30)
    ):
        triggers_met.append("heavy_rainfall")

    if (
        policy.get("covers_aqi")
        and aqi.get("aqi_pm25") is not None
        and aqi["aqi_pm25"] >= policy.get("aqi_threshold", 250)
    ):
        triggers_met.append("hazardous_aqi")

    return bool(triggers_met), triggers_met