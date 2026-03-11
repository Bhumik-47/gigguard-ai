def calculate_risk(rainfall, aqi, wind_speed):

    rainfall_score = rainfall / 100
    aqi_score = aqi / 500
    wind_score = wind_speed / 50

    risk_score = (
        rainfall_score * 0.5 +
        aqi_score * 0.3 +
        wind_score * 0.2
    )

    return round(risk_score, 2)
