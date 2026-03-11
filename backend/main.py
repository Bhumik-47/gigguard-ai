from risk_engine import calculate_risk
from payout_engine import calculate_payout


def run_demo():

    rainfall = 70
    aqi = 280
    wind_speed = 20

    coverage = 1000

    risk_score = calculate_risk(rainfall, aqi, wind_speed)
    payout = calculate_payout(risk_score, coverage)

    print("=== GigGuard AI Demo ===")
    print("Rainfall:", rainfall)
    print("AQI:", aqi)
    print("Wind Speed:", wind_speed)
    print("Risk Score:", risk_score)
    print("Insurance Payout:", payout)


if __name__ == "__main__":
    run_demo()
