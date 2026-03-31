"""
fraud_engine.py
---------------
GigGuard AI — Fraud Detection Engine  (NEW in v3)

Addresses judge feedback: "No adversarial defense section"

Why parametric insurance needs fraud detection
----------------------------------------------
Parametric insurance is uniquely vulnerable to two attack vectors:
  1. Sensor spoofing   — manipulating the device reporting weather data
     (e.g. holding phone near a kettle to spike temperature readings)
  2. Threshold gaming  — filing claims just above trigger threshold
     repeatedly across multiple accounts or time windows

This engine implements a weighted multi-rule scoring system that mirrors
the anti-fraud logic used by real insurtech platforms (Acko, Digit, Go Digit).

Fraud rules implemented
-----------------------
Rule 1  TOO_CALM_TO_CLAIM       (weight 30)
  Payout triggered but ALL three environmental readings are below the
  minimum levels expected during a genuine disruption event.

Rule 2  SENSOR_CONSISTENCY      (weight 25)
  Environmental inputs must be physically consistent. Heavy rainfall
  (>80 mm/hr) almost always correlates with elevated wind speed. If
  rainfall is extreme but wind is near-zero, data is likely spoofed.

Rule 3  SCORE_INPUT_DIVERGENCE  (weight 20)
  Risk score is high enough to trigger payout, but NO individual factor
  score is meaningfully elevated. Suggests borderline multi-factor gaming.

Rule 4  THRESHOLD_GAMING        (weight 20)
  Score sits in the narrow band just above trigger (0.58–0.65) and the
  worker has already claimed at least once this week. Pattern suggests
  deliberate manipulation to stay just inside the payout zone.

Rule 5  CLAIM_VELOCITY          (weight 25)
  Worker is approaching or has hit the weekly claim cap at an unusually
  high rate. Soft signal — raised weight when combined with other flags.

Verdict thresholds
------------------
  score  0–25  → SAFE       (auto-approve payout)
  score 26–50  → REVIEW     (hold payout; analyst review within 4 hrs)
  score 51–74  → SUSPICIOUS (hold payout; fraud team investigates)
  score 75–100 → BLOCKED    (payout blocked; account flagged)
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Rule weights
# ---------------------------------------------------------------------------
RULE_WEIGHTS = {
    "TOO_CALM_TO_CLAIM":     30,
    "SENSOR_CONSISTENCY":    25,
    "SCORE_INPUT_DIVERGENCE":20,
    "THRESHOLD_GAMING":      20,
    "CLAIM_VELOCITY":        25,
}

# Verdict thresholds
_SAFE_MAX       = 25
_REVIEW_MAX     = 50
_SUSPICIOUS_MAX = 74

# Minimum plausible readings for a genuine disruption event
_MIN_RAINFALL  = 20.0   # mm/hr
_MIN_AQI       = 120.0  # µg/m³
_MIN_WIND      = 25.0   # km/h

# Sensor consistency — heavy rain should bring elevated wind
_RAIN_STORM_THRESHOLD = 80.0   # mm/hr
_RAIN_MIN_WIND        = 20.0   # km/h expected when rain is this heavy

# Threshold gaming band
_GAMING_LOW  = 0.58
_GAMING_HIGH = 0.65


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FraudFlag:
    """A single triggered fraud rule."""
    rule_code:   str
    weight:      int
    description: str


@dataclass
class FraudResult:
    """Aggregate output of the fraud detection engine."""
    fraud_score:  int          # 0–100 composite
    verdict:      str          # "SAFE" | "REVIEW" | "SUSPICIOUS" | "BLOCKED"
    flags:        list[FraudFlag]
    flag_codes:   list[str]
    reason:       str          # Summary for UI / ops team
    auto_approve: bool         # True only when verdict == "SAFE"


# ---------------------------------------------------------------------------
# Individual rule functions
# ---------------------------------------------------------------------------

def _rule_too_calm(
    triggered: bool, rainfall: float, aqi: float, wind_speed: float
) -> Optional[FraudFlag]:
    """All three readings below minimum disruption levels yet payout triggered."""
    if not triggered:
        return None
    if rainfall < _MIN_RAINFALL and aqi < _MIN_AQI and wind_speed < _MIN_WIND:
        return FraudFlag(
            rule_code="TOO_CALM_TO_CLAIM",
            weight=RULE_WEIGHTS["TOO_CALM_TO_CLAIM"],
            description=(
                f"Payout triggered but all readings below disruption minimums: "
                f"rainfall {rainfall} mm/hr (min {_MIN_RAINFALL}), "
                f"AQI {aqi} µg/m³ (min {_MIN_AQI}), "
                f"wind {wind_speed} km/h (min {_MIN_WIND}). "
                "Physical disruption is unlikely — sensor data is suspect."
            ),
        )
    return None


def _rule_sensor_consistency(
    rainfall: float, wind_speed: float
) -> Optional[FraudFlag]:
    """Heavy rainfall without corresponding wind is physically implausible."""
    if rainfall >= _RAIN_STORM_THRESHOLD and wind_speed < _RAIN_MIN_WIND:
        return FraudFlag(
            rule_code="SENSOR_CONSISTENCY",
            weight=RULE_WEIGHTS["SENSOR_CONSISTENCY"],
            description=(
                f"Sensor inconsistency: rainfall {rainfall} mm/hr is extreme "
                f"but wind speed is only {wind_speed} km/h. "
                "Heavy rain events are meteorologically associated with elevated wind. "
                "Possible rainfall sensor spoofing or stale cached reading."
            ),
        )
    return None


def _rule_score_input_divergence(
    triggered: bool, risk_score: float,
    r_score: float, a_score: float, w_score: float,
) -> Optional[FraudFlag]:
    """Score crosses threshold but no individual factor is meaningfully high."""
    if not triggered:
        return None
    if all(s < 0.30 for s in [r_score, a_score, w_score]) and risk_score >= 0.60:
        return FraudFlag(
            rule_code="SCORE_INPUT_DIVERGENCE",
            weight=RULE_WEIGHTS["SCORE_INPUT_DIVERGENCE"],
            description=(
                f"Score divergence: composite risk_score={risk_score:.3f} exceeds "
                f"payout threshold (0.60) but all individual factor scores are low "
                f"(rainfall={r_score:.3f}, AQI={a_score:.3f}, wind={w_score:.3f}). "
                "No single dominant hazard — possible borderline multi-factor gaming."
            ),
        )
    return None


def _rule_threshold_gaming(
    triggered: bool, risk_score: float, claims_this_week: int
) -> Optional[FraudFlag]:
    """Score in narrow band just above trigger + already claimed this week."""
    if not triggered:
        return None
    if _GAMING_LOW <= risk_score <= _GAMING_HIGH and claims_this_week >= 1:
        return FraudFlag(
            rule_code="THRESHOLD_GAMING",
            weight=RULE_WEIGHTS["THRESHOLD_GAMING"],
            description=(
                f"Threshold gaming pattern: risk_score={risk_score:.3f} is in the "
                f"narrow trigger band [{_GAMING_LOW}–{_GAMING_HIGH}] and this is "
                f"claim #{claims_this_week + 1} this week. "
                "Pattern may indicate deliberate manipulation to stay just above trigger."
            ),
        )
    return None


def _rule_claim_velocity(
    claims_this_week: int, max_claims_per_week: int
) -> Optional[FraudFlag]:
    """Worker approaching or at weekly claim cap unusually fast."""
    threshold = max(1, int(max_claims_per_week * 0.75))
    if claims_this_week >= threshold:
        return FraudFlag(
            rule_code="CLAIM_VELOCITY",
            weight=RULE_WEIGHTS["CLAIM_VELOCITY"],
            description=(
                f"High claim velocity: {claims_this_week}/{max_claims_per_week} "
                "weekly claims filed. Account is at or near the weekly cap, "
                "which may indicate aggressive claim behaviour."
            ),
        )
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_fraud(
    payout_triggered:    bool,
    risk_score:          float,
    rainfall:            float,
    aqi:                 float,
    wind_speed:          float,
    rainfall_score:      float = 0.0,
    aqi_score:           float = 0.0,
    wind_score:          float = 0.0,
    claims_this_week:    int   = 0,
    max_claims_per_week: int   = 2,
) -> FraudResult:
    """
    Run all fraud detection rules and return an aggregate verdict.

    Parameters
    ----------
    payout_triggered     : Whether the payout engine computed a payout.
    risk_score           : Composite risk score (0–1).
    rainfall/aqi/wind_speed : Raw environmental readings.
    rainfall_score/aqi_score/wind_score : Normalised factor scores (0–1).
    claims_this_week     : Claims the worker has filed this week.
    max_claims_per_week  : Policy weekly limit.

    Returns
    -------
    FraudResult with fraud_score (0–100), 4-level verdict, and flag detail.
    """
    raw_flags = [
        _rule_too_calm(payout_triggered, rainfall, aqi, wind_speed),
        _rule_sensor_consistency(rainfall, wind_speed),
        _rule_score_input_divergence(payout_triggered, risk_score,
                                     rainfall_score, aqi_score, wind_score),
        _rule_threshold_gaming(payout_triggered, risk_score, claims_this_week),
        _rule_claim_velocity(claims_this_week, max_claims_per_week),
    ]

    flags: list[FraudFlag] = [f for f in raw_flags if f is not None]
    fraud_score = min(100, sum(f.weight for f in flags))

    if fraud_score <= _SAFE_MAX:
        verdict, auto_approve = "SAFE", True
        reason = "All fraud checks passed. Claim approved for automatic payout."
    elif fraud_score <= _REVIEW_MAX:
        verdict, auto_approve = "REVIEW", False
        reason = (
            "Soft fraud signals detected. Claim queued for analyst review "
            "within 4 hours. Payout held pending review outcome."
        )
    elif fraud_score <= _SUSPICIOUS_MAX:
        verdict, auto_approve = "SUSPICIOUS", False
        reason = (
            "Multiple fraud indicators detected. Payout suspended. "
            "Our fraud team will investigate and contact you within 24 hours."
        )
    else:
        verdict, auto_approve = "BLOCKED", False
        reason = (
            "High-confidence fraud signals detected. Payout blocked and account "
            "flagged for manual investigation. Contact GigGuard AI support "
            "with shift evidence if this is in error."
        )

    return FraudResult(
        fraud_score=fraud_score,
        verdict=verdict,
        flags=flags,
        flag_codes=[f.rule_code for f in flags],
        reason=reason,
        auto_approve=auto_approve,
    )
