"""
risk_engine.py
--------------
GigGuard AI — Risk Engine

Computes a normalised disruption risk score (0.0 – 1.0) from three
environmental parameters:
  • rainfall   (mm/hr)
  • aqi        (µg/m³, PM2.5)
  • wind_speed (km/h)

Each parameter is compared against a "safe" baseline and a "critical"
ceiling.  The normalised value (0‒1) for each parameter is then combined
using a weighted average to produce the final score.

Weights reflect real-world impact on two-wheeler delivery safety:
  rainfall    → 50 %  (greatest immediate hazard)
  aqi         → 30 %  (health risk, reduces work hours)
  wind_speed  → 20 %  (stability / control risk)
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Thresholds — tune these for the hackathon demo as needed
# ---------------------------------------------------------------------------

# Below SAFE  → component score = 0.0 (no contribution to risk)
# Above CRIT  → component score = 1.0 (maximum contribution)
# Between the two → linearly interpolated

RAINFALL_SAFE  =  10.0   # mm/hr  — light drizzle, negligible impact
RAINFALL_CRIT  = 100.0   # mm/hr  — heavy downpour

AQI_SAFE       = 100.0   # µg/m³  — "Satisfactory" band (CPCB scale)
AQI_CRIT       = 400.0   # µg/m³  — "Severe" / "Hazardous"

WIND_SAFE      =  20.0   # km/h   — light breeze
WIND_CRIT      =  80.0   # km/h   — storm-force gusts

# Contribution weights (must sum to 1.0)
WEIGHT_RAINFALL   = 0.50
WEIGHT_AQI        = 0.30
WEIGHT_WIND_SPEED = 0.20


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _normalise(value: float, safe: float, critical: float) -> float:
    """
    Linearly map `value` onto [0, 1] using the safe/critical band.
    Values at or below `safe`    → 0.0
    Values at or above `critical`→ 1.0
    """
    if value <= safe:
        return 0.0
    if value >= critical:
        return 1.0
    return (value - safe) / (critical - safe)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class RiskResult:
    """Structured result returned by calculate_risk()."""
    rainfall: float
    aqi: float
    wind_speed: float
    rainfall_score: float   # normalised component (0‒1)
    aqi_score: float        # normalised component (0‒1)
    wind_score: float       # normalised component (0‒1)
    risk_score: float       # final weighted score  (0‒1)
    risk_level: str         # human-readable label


def _risk_label(score: float) -> str:
    """Return a human-readable risk level string."""
    if score < 0.40:
        return "LOW"
    if score < 0.70:
        return "MEDIUM"
    if score < 0.90:
        return "HIGH"
    return "CRITICAL"


def calculate_risk(
    rainfall: float,
    aqi: float,
    wind_speed: float,
) -> RiskResult:
    """
    Calculate the overall disruption risk score.

    Parameters
    ----------
    rainfall   : Rainfall intensity in mm/hr
    aqi        : Air Quality Index (PM2.5) in µg/m³
    wind_speed : Wind speed in km/h

    Returns
    -------
    RiskResult dataclass with all component scores and the final score.
    """

    # Step 1 – normalise each environmental parameter to [0, 1]
    r_score = _normalise(rainfall,   RAINFALL_SAFE, RAINFALL_CRIT)
    a_score = _normalise(aqi,        AQI_SAFE,      AQI_CRIT)
    w_score = _normalise(wind_speed, WIND_SAFE,     WIND_CRIT)

    # Step 2 – weighted average to get the final risk score
    risk_score = (
        WEIGHT_RAINFALL   * r_score
        + WEIGHT_AQI        * a_score
        + WEIGHT_WIND_SPEED * w_score
    )

    # Step 3 – clamp to [0, 1] as a safety measure
    risk_score = max(0.0, min(1.0, round(risk_score, 4)))

    return RiskResult(
        rainfall=rainfall,
        aqi=aqi,
        wind_speed=wind_speed,
        rainfall_score=round(r_score, 4),
        aqi_score=round(a_score, 4),
        wind_score=round(w_score, 4),
        risk_score=risk_score,
        risk_level=_risk_label(risk_score),
    )
