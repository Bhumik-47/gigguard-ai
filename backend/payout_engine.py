"""
payout_engine.py
----------------
GigGuard AI — Payout Engine

Given a risk score (0.0 – 1.0) and a worker's coverage plan, this module
decides whether a parametric payout is triggered and calculates the exact
rupee amount.

Payout tiers (parametric, no-claim-needed):
  risk < 0.60  →  0 %  payout  (no disruption)
  risk < 0.75  → 30 %  payout  (mild disruption)
  risk < 0.90  → 50 %  payout  (significant disruption)
  risk ≥ 0.90  → 80 %  payout  (severe / critical disruption)

A small platform fee (1 %) is deducted from the gross payout to cover
processing costs, reflecting a realistic product design.
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Platform fee
# ---------------------------------------------------------------------------

PLATFORM_FEE_RATE = 0.01   # 1 % of gross payout


# ---------------------------------------------------------------------------
# Payout tier table
# ---------------------------------------------------------------------------
# Each entry is (risk_threshold, payout_percentage).
# Evaluated top-down; the first threshold the score falls *below* is used.
# A sentinel entry at the end handles the ≥ 0.90 case.

PAYOUT_TIERS = [
    (0.60, 0.00),   # risk < 0.60  → no payout
    (0.75, 0.30),   # risk < 0.75  → 30 %
    (0.90, 0.50),   # risk < 0.90  → 50 %
    (1.01, 0.80),   # risk ≥ 0.90  → 80 %  (1.01 acts as ∞ sentinel)
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CoveragePlan:
    """Represents a worker's active insurance plan."""
    plan_name: str          = "Weekly Shield"
    premium: float          = 49.0            # INR per week
    coverage_cap: float     = 2500.0          # max payout per event (INR)
    max_claims_per_week: int = 2


@dataclass
class PayoutResult:
    """Structured result returned by calculate_payout()."""
    risk_score: float
    risk_level: str
    plan: CoveragePlan
    payout_percentage: float        # e.g. 0.50 → 50 %
    gross_payout: float             # coverage_cap × payout_percentage
    platform_fee: float             # 1 % of gross
    net_payout: float               # gross − fee
    payout_triggered: bool
    message: str


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _payout_percentage(risk_score: float) -> float:
    """Return the payout percentage for a given risk score."""
    for threshold, percentage in PAYOUT_TIERS:
        if risk_score < threshold:
            return percentage
    # Fallback — should never be reached due to the sentinel
    return 0.80


def calculate_payout(
    risk_score: float,
    risk_level: str,
    plan: Optional[CoveragePlan] = None,
) -> PayoutResult:
    """
    Calculate the parametric insurance payout.

    Parameters
    ----------
    risk_score  : Float in [0, 1] from the risk engine.
    risk_level  : Human-readable label ("LOW", "MEDIUM", "HIGH", "CRITICAL").
    plan        : CoveragePlan instance; defaults to the Weekly Shield plan.

    Returns
    -------
    PayoutResult dataclass with all financial details.
    """

    if plan is None:
        plan = CoveragePlan()

    # Step 1 – determine which payout tier applies
    pct = _payout_percentage(risk_score)

    # Step 2 – compute monetary amounts
    gross = round(plan.coverage_cap * pct, 2)
    fee   = round(gross * PLATFORM_FEE_RATE, 2)
    net   = round(gross - fee, 2)

    # Step 3 – decide trigger status and compose a message
    triggered = pct > 0.0

    if not triggered:
        msg = (
            f"Risk score {risk_score:.2f} is below the payout threshold (0.60). "
            "No disruption event detected — stay safe out there!"
        )
    else:
        msg = (
            f"Automatic payout triggered due to environmental disruption. "
            f"Risk score {risk_score:.2f} ({risk_level}) qualifies for "
            f"{int(pct * 100)}% coverage. ₹{net:.0f} will be transferred via UPI."
        )

    return PayoutResult(
        risk_score=risk_score,
        risk_level=risk_level,
        plan=plan,
        payout_percentage=pct,
        gross_payout=gross,
        platform_fee=fee,
        net_payout=net,
        payout_triggered=triggered,
        message=msg,
    )
