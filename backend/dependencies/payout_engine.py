"""
payout_engine.py
----------------
GigGuard AI — Payout Engine  (v4 — Actuarial Intelligence Layer)

What's new in v4
-----------------
1. Event Probability Table (risk_score → P(event))
   Maps current risk score to a probability of a genuine disruption event.
   Used to compute actuarially fair Expected Loss.

2. Expected Loss Calculation
   expected_loss = P(event | risk_score) × coverage_cap
   This is the core actuarial metric — what the insurer expects to pay out
   on average for a policy with this risk profile right now.

3. Dynamic Premium Pricing
   dynamic_premium = base_premium × (1 + risk_score)
   At risk_score=0.0 → premium equals base rate (₹49).
   At risk_score=1.0 → premium doubles (₹98).
   This demonstrates risk-adjusted pricing — a key insurance concept.

4. Risk Loading Factor
   An insurance "safety loading" applied to payouts to reflect:
     • Parameter uncertainty (higher anomaly → higher loading)
     • Claims history (repeat claimants get a loading applied)
   final_payout = net_payout × (1 - risk_loading)
   risk_loading is capped at 0.30 (30% max reduction).

5. Claim Frequency Adjustment
   If the worker has filed multiple claims this period, payouts taper:
     1st claim  → 100% of calculated payout
     2nd claim  → 80%
     3rd claim  → 60%
     4th+ claim → 40%
   This prevents repeated gaming of the parametric trigger.

6. Decision Explanation
   Every PayoutResult now includes a payout_explanation field that
   narrates the financial decision in plain language.
"""

from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Financial parameters
# ---------------------------------------------------------------------------
PLATFORM_FEE_RATE  = 0.10    # 10% platform operating fee
RESERVE_MULTIPLIER = 1.25    # Solvency capital buffer
LOADING_FACTOR     = 1.40    # Premium loading (ops + profit + reinsurance)

BASE_PREMIUM       = 49.0    # INR per week (base rate at zero risk)

# Risk loading: uncertainty surcharge on payout (reduces net to worker)
# Applied when anomaly detected or repeat claims present
BASE_RISK_LOADING  = 0.05    # 5% base loading on all claims
ANOMALY_LOADING    = 0.10    # +10% when anomaly detected
REPEAT_LOADING     = 0.08    # +8% per repeat claim (2nd, 3rd, ...)
MAX_RISK_LOADING   = 0.30    # Cap at 30% total loading

# Claim frequency payout multipliers
CLAIM_FREQ_MULTIPLIERS = {
    1: 1.00,   # first claim this period
    2: 0.80,   # second claim
    3: 0.60,   # third claim
    4: 0.40,   # fourth or more
}


# ---------------------------------------------------------------------------
# Event probability table
# P(disruption event | risk_score_band)
# Calibrated from: IMD historical extreme weather days in Delhi NCR
# × gig platform order cancellation rates during those periods
# ---------------------------------------------------------------------------
_EVENT_PROB_TABLE = [
    (0.00, 0.35, 0.02),   # LOW:      2% probability
    (0.35, 0.60, 0.15),   # MEDIUM:  15% probability
    (0.60, 0.75, 0.40),   # HIGH-1:  40% probability
    (0.75, 0.90, 0.65),   # HIGH-2:  65% probability
    (0.90, 1.01, 0.90),   # CRITICAL: 90% probability
]


# ---------------------------------------------------------------------------
# Historical tier probabilities (for E[weekly loss] actuarial model)
# ---------------------------------------------------------------------------
_TIER_PROBS = {
    "NO_PAYOUT":   0.65,
    "MILD":        0.18,
    "SIGNIFICANT": 0.12,
    "CRITICAL":    0.05,
}

PAYOUT_TIERS = [
    (0.60, 0.00, "NO_PAYOUT",   "Risk below trigger threshold"),
    (0.75, 0.30, "MILD",        "Mild disruption — moderate conditions"),
    (0.90, 0.50, "SIGNIFICANT", "Significant disruption — severe conditions"),
    (1.01, 0.80, "CRITICAL",    "Critical disruption — emergency conditions"),
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CoveragePlan:
    """Worker's active insurance plan."""
    plan_name:            str   = "Weekly Shield"
    premium:              float = 49.0
    coverage_cap:         float = 2500.0
    max_claims_per_week:  int   = 2
    max_claims_per_month: int   = 6


@dataclass
class ActuarialSummary:
    """Full actuarial model output."""
    pure_premium:           float
    loaded_premium:         float
    premium_adequacy:       str
    expected_loss_ratio:    float
    claims_reserve:         float
    expected_weekly_payout: float
    # v4 new
    event_probability:      float   # P(event | current risk_score)
    expected_loss:          float   # P(event) × coverage_cap
    dynamic_premium:        float   # base_premium × (1 + risk_score)
    risk_loading:           float   # safety loading applied to this claim
    claim_adjustment:       float   # frequency-based payout multiplier


@dataclass
class PayoutResult:
    """Full structured payout output — v4."""
    risk_score:        float
    risk_level:        str
    plan:              CoveragePlan

    tier_label:        str
    tier_desc:         str
    payout_percentage: float
    coverage_cap:      float

    # Financial layers
    gross_payout:        float   # coverage_cap × payout_pct
    platform_fee:        float   # 10% of gross
    net_payout:          float   # gross − fee

    # v4 adjustments
    risk_loading:        float   # safety loading fraction
    claim_adjustment:    float   # frequency multiplier
    final_payout:        float   # net × (1−loading) × freq_multiplier

    # Exclusion-adjusted (set by apply_exclusion_to_payout)
    exclusion_applied:    bool  = False
    exclusion_code:       str   = "SAFE"
    adjusted_net_payout:  float = 0.0

    payout_triggered:   bool  = False
    message:            str   = ""
    payout_explanation: str   = ""   # v4 NEW — plain-language financial narrative

    actuarial: Optional[ActuarialSummary] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_tier(risk_score: float) -> tuple[float, str, str]:
    for threshold, pct, label, desc in PAYOUT_TIERS:
        if risk_score < threshold:
            return pct, label, desc
    return 0.80, "CRITICAL", "Critical disruption — emergency conditions"


def _event_probability(risk_score: float) -> float:
    """Look up P(disruption event) from the risk score band table."""
    for lo, hi, prob in _EVENT_PROB_TABLE:
        if lo <= risk_score < hi:
            return prob
    return 0.90


def _dynamic_premium(risk_score: float) -> float:
    """
    Risk-adjusted premium pricing.
    premium = base_premium × (1 + risk_score)
    """
    return round(BASE_PREMIUM * (1.0 + risk_score), 2)


def _compute_risk_loading(
    anomaly_detected: bool,
    claims_this_period: int,
) -> float:
    """
    Compute the risk loading factor for this specific claim.
    loading = base + anomaly_component + repeat_claim_component
    Capped at MAX_RISK_LOADING.
    """
    loading = BASE_RISK_LOADING
    if anomaly_detected:
        loading += ANOMALY_LOADING
    # Each claim beyond the first adds a repeat loading
    repeat_count = max(0, claims_this_period - 1)
    loading += repeat_count * REPEAT_LOADING
    return round(min(loading, MAX_RISK_LOADING), 3)


def _claim_frequency_multiplier(claim_number: int) -> float:
    """Return the payout multiplier based on claim count this period."""
    return CLAIM_FREQ_MULTIPLIERS.get(claim_number, 0.40)


def _build_actuarial(
    plan: CoveragePlan,
    risk_score: float,
    anomaly_detected: bool = False,
    claims_this_period: int = 1,
) -> ActuarialSummary:
    """Compute the full actuarial model for this policy and risk state."""
    # Weekly expected gross loss
    expected_gross = sum(
        _TIER_PROBS[label] * (plan.coverage_cap * pct)
        for _, pct, label, _ in PAYOUT_TIERS
        if label != "NO_PAYOUT"
    )
    expected_net   = round(expected_gross * (1 - PLATFORM_FEE_RATE), 2)
    pure_premium   = expected_net
    loaded_premium = round(pure_premium * LOADING_FACTOR, 2)
    loss_ratio     = round(pure_premium / plan.premium, 3) if plan.premium else 0.0
    reserve        = round(expected_gross * RESERVE_MULTIPLIER, 2)

    if plan.premium >= loaded_premium * 0.90:
        adequacy = "ADEQUATE"
    elif plan.premium < pure_premium:
        adequacy = "UNDER-PRICED"
    else:
        adequacy = "OVER-PRICED"

    # v4 additions
    p_event      = _event_probability(risk_score)
    exp_loss     = round(p_event * plan.coverage_cap, 2)
    dyn_premium  = _dynamic_premium(risk_score)
    risk_load    = _compute_risk_loading(anomaly_detected, claims_this_period)
    claim_adj    = _claim_frequency_multiplier(claims_this_period)

    return ActuarialSummary(
        pure_premium=round(pure_premium, 2),
        loaded_premium=loaded_premium,
        premium_adequacy=adequacy,
        expected_loss_ratio=loss_ratio,
        claims_reserve=reserve,
        expected_weekly_payout=round(expected_net, 2),
        event_probability=round(p_event, 3),
        expected_loss=exp_loss,
        dynamic_premium=dyn_premium,
        risk_loading=risk_load,
        claim_adjustment=claim_adj,
    )


def _build_payout_explanation(
    pct: float, tier: str,
    gross: float, fee: float, net: float,
    loading: float, adj: float, final: float,
    p_event: float, exp_loss: float, dyn_premium: float,
    triggered: bool,
) -> str:
    """Generate a plain-language payout decision narrative."""
    if not triggered:
        return (
            f"No payout triggered. Current risk profile implies a {p_event:.0%} "
            f"probability of a disruption event, below the 60% confidence trigger. "
            f"Expected loss at current conditions: ₹{exp_loss:.0f}. "
            f"Risk-adjusted premium for this risk state: ₹{dyn_premium:.0f}/week."
        )

    parts = [
        f"{tier} tier activated ({int(pct * 100)}% of coverage cap). "
        f"Gross payout: ₹{gross:.0f}.",
        f"Platform operating fee (10%): −₹{fee:.0f}. Net payout: ₹{net:.0f}.",
    ]
    if loading > BASE_RISK_LOADING:
        parts.append(
            f"Risk loading factor {loading:.0%} applied "
            f"(base 5% + conditions surcharge): −₹{net - net*(1-loading):.0f}."
        )
    if adj < 1.0:
        parts.append(
            f"Claim frequency adjustment {adj:.0%} applied "
            f"(repeat claim tapering policy)."
        )
    parts.append(
        f"Final transfer to worker UPI: ₹{final:.0f}. "
        f"Event probability at current risk state: {p_event:.0%}. "
        f"Expected loss: ₹{exp_loss:.0f}. "
        f"Risk-adjusted premium this period: ₹{dyn_premium:.0f}/week."
    )
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_payout(
    risk_score:         float,
    risk_level:         str,
    plan:               Optional[CoveragePlan] = None,
    include_actuarial:  bool = True,
    anomaly_detected:   bool = False,
    claims_this_period: int  = 1,
) -> PayoutResult:
    """
    Calculate parametric payout with full actuarial and AI-loading adjustments.

    Parameters
    ----------
    risk_score         : 0–1 from risk engine.
    risk_level         : "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    plan               : CoveragePlan; defaults to Weekly Shield.
    include_actuarial  : Attach ActuarialSummary.
    anomaly_detected   : From risk engine — increases risk_loading.
    claims_this_period : Claim count this week — triggers frequency adjustment.
    """
    if plan is None:
        plan = CoveragePlan()

    pct, tier_label, tier_desc = _get_tier(risk_score)

    # Base financial layers
    gross = round(plan.coverage_cap * pct, 2)
    fee   = round(gross * PLATFORM_FEE_RATE, 2)
    net   = round(gross - fee, 2)

    # v4 adjustments
    loading   = _compute_risk_loading(anomaly_detected, claims_this_period)
    claim_adj = _claim_frequency_multiplier(claims_this_period)
    final     = round(net * (1.0 - loading) * claim_adj, 2)

    triggered = pct > 0.0

    # Actuarial model
    actuarial = _build_actuarial(
        plan, risk_score, anomaly_detected, claims_this_period
    ) if include_actuarial else None

    p_event   = _event_probability(risk_score)
    exp_loss  = round(p_event * plan.coverage_cap, 2)
    dyn_prem  = _dynamic_premium(risk_score)

    # Messages
    if not triggered:
        msg = (
            f"Risk score {risk_score:.3f} is below the payout trigger (0.60). "
            "No disruption — stay safe and keep earning!"
        )
    else:
        msg = (
            f"Automatic payout triggered — {tier_label} tier "
            f"({int(pct * 100)}% of coverage cap). "
            f"Gross: ₹{gross:.0f} → Fee: ₹{fee:.0f} → Net: ₹{net:.0f} → "
            f"Final (after loading & frequency adj): ₹{final:.0f}."
        )

    explanation = _build_payout_explanation(
        pct, tier_label, gross, fee, net, loading, claim_adj, final,
        p_event, exp_loss, dyn_prem, triggered,
    )

    return PayoutResult(
        risk_score=risk_score, risk_level=risk_level, plan=plan,
        tier_label=tier_label, tier_desc=tier_desc,
        payout_percentage=pct,
        coverage_cap=plan.coverage_cap,
        gross_payout=gross, platform_fee=fee, net_payout=net,
        risk_loading=loading,
        claim_adjustment=claim_adj,
        final_payout=final,
        exclusion_applied=False, exclusion_code="SAFE",
        adjusted_net_payout=final,   # starts equal to final; exclusion can reduce further
        payout_triggered=triggered,
        message=msg,
        payout_explanation=explanation,
        actuarial=actuarial,
    )


def apply_exclusion_to_payout(
    payout:           PayoutResult,
    exclusion_code:   str,
    is_partial:       bool,
    reduction_pct:    float,
    exclusion_reason: str,
) -> PayoutResult:
    """Apply exclusion adjustment — interface unchanged from v3."""
    if exclusion_code == "SAFE":
        return payout

    if is_partial:
        adjusted = round(payout.final_payout * (1.0 - reduction_pct), 2)
        payout.message = (
            f"[PARTIAL EXCLUSION — {exclusion_code}] "
            f"Payout reduced by {int(reduction_pct * 100)}%: "
            f"₹{payout.final_payout:.0f} → ₹{adjusted:.0f}. {exclusion_reason}"
        )
    else:
        adjusted = 0.0
        payout.message = (
            f"[FULL EXCLUSION — {exclusion_code}] Payout voided. {exclusion_reason}"
        )

    payout.exclusion_applied   = True
    payout.exclusion_code      = exclusion_code
    payout.adjusted_net_payout = adjusted
    return payout
