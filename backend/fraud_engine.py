"""
fraud_engine.py
---------------
GigGuard AI — Fraud Detection Engine  (v4 — Fraud Intelligence Layer)

What's new in v4
-----------------
1. Normalised fraud_score (0.0–1.0)
   Previous version returned an integer 0–100.
   v4 normalises to 0.0–1.0 for consistency with other engine outputs.
   Integer raw_score is still returned for human readability.

2. Anomaly Correlation Rule  (NEW)
   Correlates the risk engine's anomaly_flag with the fraud signals.
   If environmental anomaly + payout triggered + conditions below minimum:
   the anomaly may be the attack vector (e.g. sensor injection attack).
   This is a more sophisticated adversarial defence.

3. Repeated Near-Threshold Pattern  (IMPROVED)
   Now looks at the full rolling buffer of risk scores (from RollingRiskBuffer)
   to detect if the worker consistently scores near the payout trigger.
   A genuine disruption event is transient; a gaming pattern is persistent.

4. fraud_flag (bool)
   Simple boolean — True if verdict is REVIEW / SUSPICIOUS / BLOCKED.
   Required by requirements spec alongside fraud_score.

5. reason + decision_explanation
   Separate fields:
     reason              — short ops team note (unchanged from v3)
     fraud_explanation   — full narrative for the decision log

6. Raw score → normalised mapping
   raw_score (int, 0–100) → fraud_score (float, 0.0–1.0)
   fraud_score = raw_score / 100.0
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

# Import buffer from risk_engine for pattern analysis
# Using a lazy import to avoid circular dependency
def _get_buffer():
    from risk_engine import RollingRiskBuffer
    return RollingRiskBuffer.get()


# ---------------------------------------------------------------------------
# Rule weights (raw integer scale 0–100)
# ---------------------------------------------------------------------------
RULE_WEIGHTS = {
    "TOO_CALM_TO_CLAIM":         30,
    "SENSOR_CONSISTENCY":        25,
    "SCORE_INPUT_DIVERGENCE":    20,
    "THRESHOLD_GAMING":          20,
    "CLAIM_VELOCITY":            25,
    "ANOMALY_CORRELATION":       25,   # v4 NEW
    "PERSISTENT_NEAR_THRESHOLD": 15,   # v4 NEW
}

# Verdict thresholds (raw 0–100 scale)
_SAFE_MAX       = 25
_REVIEW_MAX     = 50
_SUSPICIOUS_MAX = 74

# Minimum plausible environmental readings for a genuine disruption
_MIN_RAINFALL = 20.0
_MIN_AQI      = 120.0
_MIN_WIND     = 25.0

# Sensor consistency thresholds
_RAIN_STORM_THRESHOLD = 80.0
_RAIN_MIN_WIND        = 20.0

# Threshold gaming band
_GAMING_LOW  = 0.58
_GAMING_HIGH = 0.65

# Near-threshold persistence: fraction of buffer in gaming band → suspicious
_PERSIST_BAND_LO  = 0.55
_PERSIST_BAND_HI  = 0.68
_PERSIST_FRACTION = 0.60   # if 60%+ of recent scores are in this band


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FraudFlag:
    rule_code:   str
    weight:      int
    description: str


@dataclass
class FraudResult:
    """Full fraud detection output — v4."""
    raw_score:    int           # 0–100 integer sum of triggered rule weights
    fraud_score:  float         # 0.0–1.0 normalised  (raw / 100)
    fraud_flag:   bool          # True if verdict != "SAFE"
    verdict:      str           # "SAFE" | "REVIEW" | "SUSPICIOUS" | "BLOCKED"
    flags:        list[FraudFlag]
    flag_codes:   list[str]
    reason:       str           # Short ops summary
    fraud_explanation: str      # Full narrative for the decision log
    auto_approve: bool


# ---------------------------------------------------------------------------
# Individual rule functions
# ---------------------------------------------------------------------------

def _rule_too_calm(
    triggered: bool, rainfall: float, aqi: float, wind_speed: float,
) -> Optional[FraudFlag]:
    if not triggered:
        return None
    if rainfall < _MIN_RAINFALL and aqi < _MIN_AQI and wind_speed < _MIN_WIND:
        return FraudFlag(
            rule_code="TOO_CALM_TO_CLAIM",
            weight=RULE_WEIGHTS["TOO_CALM_TO_CLAIM"],
            description=(
                f"Payout triggered but all readings below disruption minimums: "
                f"rainfall {rainfall} mm/hr, AQI {aqi} µg/m³, wind {wind_speed} km/h. "
                "No physical basis for disruption claim."
            ),
        )
    return None


def _rule_sensor_consistency(rainfall: float, wind_speed: float) -> Optional[FraudFlag]:
    if rainfall >= _RAIN_STORM_THRESHOLD and wind_speed < _RAIN_MIN_WIND:
        return FraudFlag(
            rule_code="SENSOR_CONSISTENCY",
            weight=RULE_WEIGHTS["SENSOR_CONSISTENCY"],
            description=(
                f"Physical inconsistency: rainfall {rainfall} mm/hr is storm-level "
                f"but wind is only {wind_speed} km/h. "
                "Meteorologically implausible — possible sensor spoofing."
            ),
        )
    return None


def _rule_score_input_divergence(
    triggered: bool, risk_score: float,
    r_score: float, a_score: float, w_score: float,
) -> Optional[FraudFlag]:
    if not triggered:
        return None
    if all(s < 0.30 for s in [r_score, a_score, w_score]) and risk_score >= 0.60:
        return FraudFlag(
            rule_code="SCORE_INPUT_DIVERGENCE",
            weight=RULE_WEIGHTS["SCORE_INPUT_DIVERGENCE"],
            description=(
                f"Score-input divergence: composite={risk_score:.3f} triggers payout "
                f"but individual factors are all low "
                f"(R={r_score:.3f}, A={a_score:.3f}, W={w_score:.3f}). "
                "No dominant hazard — multi-factor borderline gaming suspected."
            ),
        )
    return None


def _rule_threshold_gaming(
    triggered: bool, risk_score: float, claims_this_week: int,
) -> Optional[FraudFlag]:
    if not triggered:
        return None
    if _GAMING_LOW <= risk_score <= _GAMING_HIGH and claims_this_week >= 1:
        return FraudFlag(
            rule_code="THRESHOLD_GAMING",
            weight=RULE_WEIGHTS["THRESHOLD_GAMING"],
            description=(
                f"Threshold gaming: score={risk_score:.3f} in narrow trigger band "
                f"[{_GAMING_LOW}–{_GAMING_HIGH}], claim #{claims_this_week + 1} this week. "
                "Pattern consistent with deliberate marginal manipulation."
            ),
        )
    return None


def _rule_claim_velocity(claims_this_week: int, max_claims_per_week: int) -> Optional[FraudFlag]:
    threshold = max(1, int(max_claims_per_week * 0.75))
    if claims_this_week >= threshold:
        return FraudFlag(
            rule_code="CLAIM_VELOCITY",
            weight=RULE_WEIGHTS["CLAIM_VELOCITY"],
            description=(
                f"High claim velocity: {claims_this_week}/{max_claims_per_week} "
                "weekly claims filed. Approaching or at weekly cap."
            ),
        )
    return None


def _rule_anomaly_correlation(
    triggered: bool,
    anomaly_flag: bool,
    rainfall: float, aqi: float, wind_speed: float,
) -> Optional[FraudFlag]:
    """
    v4 NEW — Correlate the risk engine's anomaly signal with the claim.

    If the anomaly_flag is True AND payout is triggered AND conditions are
    below minimum disruption levels, the anomaly may be the attack mechanism
    (e.g. injecting a fake spike into the sensor feed to inflate the score).
    """
    if not triggered or not anomaly_flag:
        return None
    below_min = (
        rainfall  < _MIN_RAINFALL
        and aqi   < _MIN_AQI
        and wind_speed < _MIN_WIND
    )
    if below_min:
        return FraudFlag(
            rule_code="ANOMALY_CORRELATION",
            weight=RULE_WEIGHTS["ANOMALY_CORRELATION"],
            description=(
                "Environmental anomaly detected by AI engine AND payout triggered, "
                "but underlying conditions are below minimum disruption thresholds. "
                "Anomaly may be the attack vector — possible sensor injection attack."
            ),
        )
    return None


def _rule_persistent_near_threshold(risk_score: float) -> Optional[FraudFlag]:
    """
    v4 NEW — Detect persistent near-threshold scores across the rolling buffer.

    A genuine severe event is transient and typically scores well above the
    trigger band. Persistent hovering just above 0.60 across multiple
    observations is a strong signal of sustained manipulation.
    """
    try:
        buf = _get_buffer()
        snap = buf.snapshot()
        scores = snap["scores"]
    except Exception:
        return None

    if len(scores) < 4:
        return None   # not enough history

    in_band = sum(1 for s in scores if _PERSIST_BAND_LO <= s <= _PERSIST_BAND_HI)
    fraction = in_band / len(scores)

    if fraction >= _PERSIST_FRACTION:
        return FraudFlag(
            rule_code="PERSISTENT_NEAR_THRESHOLD",
            weight=RULE_WEIGHTS["PERSISTENT_NEAR_THRESHOLD"],
            description=(
                f"{in_band}/{len(scores)} recent risk scores ({fraction:.0%}) "
                f"persistently in the narrow trigger band "
                f"[{_PERSIST_BAND_LO}–{_PERSIST_BAND_HI}]. "
                "Genuine disruption events are transient; sustained proximity suggests "
                "deliberate manipulation."
            ),
        )
    return None


# ---------------------------------------------------------------------------
# Explanation builder
# ---------------------------------------------------------------------------

def _build_fraud_explanation(
    flags: list[FraudFlag],
    verdict: str,
    raw_score: int,
    fraud_score: float,
) -> str:
    if not flags:
        return (
            "All fraud detection rules passed. No suspicious patterns detected. "
            f"Fraud score: {fraud_score:.2f} (SAFE threshold ≤ 0.25). "
            "Claim approved for automatic processing."
        )

    rule_names = ", ".join(f.rule_code for f in flags)
    parts = [
        f"Fraud analysis verdict: {verdict} (score {fraud_score:.2f}, raw {raw_score}/100). "
        f"Rules triggered: {rule_names}."
    ]

    for flag in flags:
        parts.append(f"[{flag.rule_code}] {flag.description}")

    if verdict == "REVIEW":
        parts.append(
            "Action: Claim held for analyst review within 4 hours. "
            "Payout suspended pending review outcome."
        )
    elif verdict == "SUSPICIOUS":
        parts.append(
            "Action: Payout suspended. Fraud team investigation initiated. "
            "Worker will be contacted within 24 hours."
        )
    elif verdict == "BLOCKED":
        parts.append(
            "Action: Payout blocked. Account flagged for manual investigation. "
            "Worker should contact GigGuard AI support with shift evidence."
        )

    return " | ".join(parts)


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
    anomaly_flag:        bool  = False,   # v4 NEW parameter
) -> FraudResult:
    """
    Run all fraud detection rules and return an aggregate verdict.

    New in v4
    ----------
    • anomaly_flag parameter wired to the anomaly_correlation rule.
    • persistent_near_threshold reads from the global RollingRiskBuffer.
    • fraud_score normalised to 0.0–1.0.
    • fraud_flag boolean added.
    • fraud_explanation narrative added.
    """
    raw_flags = [
        _rule_too_calm(payout_triggered, rainfall, aqi, wind_speed),
        _rule_sensor_consistency(rainfall, wind_speed),
        _rule_score_input_divergence(payout_triggered, risk_score,
                                     rainfall_score, aqi_score, wind_score),
        _rule_threshold_gaming(payout_triggered, risk_score, claims_this_week),
        _rule_claim_velocity(claims_this_week, max_claims_per_week),
        _rule_anomaly_correlation(payout_triggered, anomaly_flag,
                                  rainfall, aqi, wind_speed),
        _rule_persistent_near_threshold(risk_score),
    ]

    flags: list[FraudFlag] = [f for f in raw_flags if f is not None]
    raw_score   = min(100, sum(f.weight for f in flags))
    fraud_score = round(raw_score / 100.0, 3)

    if raw_score <= _SAFE_MAX:
        verdict, auto_approve = "SAFE", True
        reason = "All fraud checks passed. Claim approved for automatic payout."
    elif raw_score <= _REVIEW_MAX:
        verdict, auto_approve = "REVIEW", False
        reason = (
            "Soft fraud signals. Claim queued for analyst review within 4 hours."
        )
    elif raw_score <= _SUSPICIOUS_MAX:
        verdict, auto_approve = "SUSPICIOUS", False
        reason = (
            "Multiple fraud indicators. Payout suspended — fraud team investigating."
        )
    else:
        verdict, auto_approve = "BLOCKED", False
        reason = (
            "High-confidence fraud signals. Payout blocked. Account flagged."
        )

    fraud_flag        = verdict != "SAFE"
    fraud_explanation = _build_fraud_explanation(flags, verdict, raw_score, fraud_score)

    return FraudResult(
        raw_score=raw_score,
        fraud_score=fraud_score,
        fraud_flag=fraud_flag,
        verdict=verdict,
        flags=flags,
        flag_codes=[f.rule_code for f in flags],
        reason=reason,
        fraud_explanation=fraud_explanation,
        auto_approve=auto_approve,
    )
