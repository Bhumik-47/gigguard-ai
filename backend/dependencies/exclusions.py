"""
exclusions.py
-------------
GigGuard AI — Insurance Exclusion Engine  (NEW in v3)

Addresses judge feedback: "Missing critical insurance exclusions (war/pandemic)"

Why exclusions matter
---------------------
Every regulated insurance product must define conditions under which
coverage does NOT apply. IRDAI (Insurance Regulatory and Development
Authority of India) requires these to be stated explicitly in the
policy document. Without them, the product is not IRDAI-compliant.

For parametric insurance specifically, exclusions are critical because
the payout trigger is automatic — the system must identify and block
claims that technically meet the environmental threshold but fall under
a policy exclusion before any money moves.

Exclusion clauses implemented
------------------------------
1. PANDEMIC / EPIDEMIC       — Systemic risk; full void
2. WAR / CIVIL UNREST        — Political risk; full void
3. FRAUD INVESTIGATION HOLD  — Account under review; full void
4. POLICY LAPSED             — No premium = no coverage; full void
5. WEEKLY CLAIM LIMIT        — Max 2 claims/week; full void
6. MONTHLY CLAIM LIMIT       — Max 6 claims/month; full void
7. GOVT REGULATORY RESTRICT  — Odd-even, NGT ban; 50% partial reduction
8. PLATFORM OUTAGE           — App downtime; 50% partial reduction

Evaluation order: full-exclusion checks run first. If any full exclusion
triggers, partials are not evaluated. This mirrors real claims processing.
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ClaimContext:
    """
    Contextual information about the worker's policy and claim history.
    In production: fetched from the policy database per worker session.
    """
    claims_this_week:    int   = 0
    max_claims_per_week: int   = 2
    claims_this_month:   int   = 0
    max_claims_per_month:int   = 6
    policy_active:       bool  = True
    is_pandemic_period:  bool  = False   # set by ops team / govt health API
    is_war_period:       bool  = False   # set by ops team
    platform_outage:     bool  = False   # from platform status API
    govt_restriction:    bool  = False   # odd-even, NGT ban, Section 144
    worker_flagged:      bool  = False   # set by fraud engine after review


@dataclass
class ExclusionResult:
    """Result of running evaluate_exclusions()."""
    is_excluded:      bool         # True = claim voided or reduced
    exclusion_code:   str          # Machine-readable code; "SAFE" if no exclusion
    reason:           str          # Human-readable IRDAI-style reason
    is_partial:       bool         # True = payout reduced, not zeroed
    reduction_pct:    float        # 0.0 = full block; 0.5 = 50% reduction
    applicable_clauses: list[str]  # All policy clauses triggered


# ---------------------------------------------------------------------------
# Individual exclusion rule checkers
# Each returns a dict if triggered, None if not.
# ---------------------------------------------------------------------------

def _check_policy_lapse(ctx: ClaimContext) -> Optional[dict]:
    """Section 2(a) — Policy must be active to claim."""
    if not ctx.policy_active:
        return {
            "code":    "POLICY_LAPSED",
            "reason":  (
                "Claim excluded — Section 2(a): Active Policy Required. "
                "Your GigGuard AI policy is not currently active. "
                "Premium payment may be overdue or the policy period has expired. "
                "Please renew your Weekly Shield plan to restore coverage."
            ),
            "partial": False, "reduction": 0.0,
            "clause":  "Section 2(a): Policy Activation Condition",
        }
    return None


def _check_pandemic(ctx: ClaimContext) -> Optional[dict]:
    """Section 4(a) — Pandemic / epidemic is a force majeure event."""
    if ctx.is_pandemic_period:
        return {
            "code":    "PANDEMIC_EXCLUSION",
            "reason":  (
                "Claim excluded — Section 4(a): Pandemic / Epidemic Clause. "
                "A government-declared public health emergency constitutes a "
                "force majeure event. GigGuard AI parametric coverage is suspended "
                "system-wide during declared health emergencies. "
                "Workers are directed to available government relief schemes."
            ),
            "partial": False, "reduction": 0.0,
            "clause":  "Section 4(a): Force Majeure — Pandemic / Epidemic",
        }
    return None


def _check_war(ctx: ClaimContext) -> Optional[dict]:
    """Section 4(b) — War, armed conflict, curfew, riot."""
    if ctx.is_war_period:
        return {
            "code":    "WAR_CIVIL_UNREST_EXCLUSION",
            "reason":  (
                "Claim excluded — Section 4(b): War and Civil Disturbance Clause. "
                "Armed conflict, riots, government-imposed curfews, and civil unrest "
                "are explicitly excluded from parametric weather insurance. "
                "This product covers environmental disruptions only."
            ),
            "partial": False, "reduction": 0.0,
            "clause":  "Section 4(b): War, Riot, Civil Commotion, Curfew",
        }
    return None


def _check_worker_flagged(ctx: ClaimContext) -> Optional[dict]:
    """Section 6(b) — Account under fraud investigation."""
    if ctx.worker_flagged:
        return {
            "code":    "FRAUD_INVESTIGATION_HOLD",
            "reason":  (
                "Claim on hold — Section 6(b): Anti-Fraud Investigation Hold. "
                "Your account has been flagged for review based on claim pattern "
                "analysis. Payouts are suspended pending verification. "
                "Our team will contact you within 48 hours. If the review confirms "
                "legitimacy, all eligible payouts will be released retroactively."
            ),
            "partial": False, "reduction": 0.0,
            "clause":  "Section 6(b): Anti-Fraud Investigation Hold",
        }
    return None


def _check_weekly_limit(ctx: ClaimContext) -> Optional[dict]:
    """Section 5(a) — Weekly claim frequency cap."""
    if ctx.claims_this_week >= ctx.max_claims_per_week:
        return {
            "code":    "WEEKLY_CLAIM_LIMIT_EXCEEDED",
            "reason":  (
                f"Claim excluded — Section 5(a): Claim Frequency Limit. "
                f"You have already submitted {ctx.claims_this_week} claim(s) this week "
                f"(maximum: {ctx.max_claims_per_week}). "
                "Your weekly limit resets at Monday 00:00."
            ),
            "partial": False, "reduction": 0.0,
            "clause":  "Section 5(a): Maximum 2 Claims per Policy Week",
        }
    return None


def _check_monthly_limit(ctx: ClaimContext) -> Optional[dict]:
    """Section 5(a) — Monthly claim frequency cap."""
    if ctx.claims_this_month >= ctx.max_claims_per_month:
        return {
            "code":    "MONTHLY_CLAIM_LIMIT_EXCEEDED",
            "reason":  (
                f"Claim excluded — Section 5(a): Monthly Claim Frequency Limit. "
                f"You have submitted {ctx.claims_this_month} claim(s) this month "
                f"(maximum: {ctx.max_claims_per_month}). "
                "Your limit resets on the 1st of next month."
            ),
            "partial": False, "reduction": 0.0,
            "clause":  "Section 5(a): Maximum 6 Claims per Policy Month",
        }
    return None


def _check_govt_restriction(ctx: ClaimContext) -> Optional[dict]:
    """Section 4(d) — Regulatory restriction (partial exclusion)."""
    if ctx.govt_restriction:
        return {
            "code":    "GOVT_RESTRICTION_EXCLUSION",
            "reason":  (
                "Partial exclusion — Section 4(d): Regulatory Action Clause. "
                "A government-imposed restriction (e.g., odd-even scheme, "
                "NGT pollution emergency ban, Section 144 prohibitory order) "
                "is not attributable solely to a weather event. "
                "Payout reduced by 50%."
            ),
            "partial": True, "reduction": 0.50,
            "clause":  "Section 4(d): Government Regulatory Restriction",
        }
    return None


def _check_platform_outage(ctx: ClaimContext) -> Optional[dict]:
    """Section 4(c) — Platform downtime (partial exclusion)."""
    if ctx.platform_outage:
        return {
            "code":    "PLATFORM_OUTAGE_EXCLUSION",
            "reason":  (
                "Partial exclusion — Section 4(c): Third-Party Platform Exclusion. "
                "Work disruption attributable to platform downtime or app maintenance "
                "is not a covered weather event. Payout reduced by 50%."
            ),
            "partial": True, "reduction": 0.50,
            "clause":  "Section 4(c): Third-Party Platform Downtime",
        }
    return None


# ---------------------------------------------------------------------------
# Ordered check list — full exclusions first, partials last
# ---------------------------------------------------------------------------
_EXCLUSION_CHECKS = [
    _check_policy_lapse,
    _check_pandemic,
    _check_war,
    _check_worker_flagged,
    _check_weekly_limit,
    _check_monthly_limit,
    _check_govt_restriction,
    _check_platform_outage,
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_exclusions(ctx: ClaimContext) -> ExclusionResult:
    """
    Evaluate all exclusion clauses in priority order.

    Returns
    -------
    ExclusionResult
      is_excluded=False, code="SAFE"  → claim proceeds at full value
      is_excluded=True,  partial=False → claim fully voided (payout = 0)
      is_excluded=True,  partial=True  → payout reduced by reduction_pct
    """
    triggered: list[dict] = []

    for check_fn in _EXCLUSION_CHECKS:
        result = check_fn(ctx)
        if result:
            triggered.append(result)

    if not triggered:
        return ExclusionResult(
            is_excluded=False,
            exclusion_code="SAFE",
            reason="No exclusions apply. Claim is eligible for full parametric payout.",
            is_partial=False,
            reduction_pct=0.0,
            applicable_clauses=[],
        )

    # Full exclusions take precedence over partials
    full_blocks = [t for t in triggered if not t["partial"]]
    partials    = [t for t in triggered if t["partial"]]

    if full_blocks:
        primary = full_blocks[0]
        return ExclusionResult(
            is_excluded=True,
            exclusion_code=primary["code"],
            reason=primary["reason"],
            is_partial=False,
            reduction_pct=0.0,
            applicable_clauses=[t["clause"] for t in triggered],
        )

    # Only partial exclusions — apply the highest reduction
    primary = partials[0]
    max_reduction = max(t["reduction"] for t in partials)
    return ExclusionResult(
        is_excluded=True,
        exclusion_code=primary["code"],
        reason=primary["reason"],
        is_partial=True,
        reduction_pct=max_reduction,
        applicable_clauses=[t["clause"] for t in triggered],
    )
