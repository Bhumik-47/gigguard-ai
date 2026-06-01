from fastapi import APIRouter,Query
from backend.models.schemas import CalculateResponse
from backend.dependencies.risk_engine   import calculate_risk, predict_risk_trend
from backend.dependencies.exclusions    import evaluate_exclusions, ClaimContext
from backend.dependencies.payout_engine import calculate_payout, apply_exclusion_to_payout, CoveragePlan
from backend.dependencies.fraud_engine  import detect_fraud

router = APIRouter()

@router.get("/calculate", response_model=CalculateResponse,
         summary="Custom risk & payout calculation", tags=["Utility"])
def calculate(
    rainfall: float = Query(default=50.0, ge=0, le=500,
                            description="Rainfall intensity mm/hr"),
    aqi: float = Query(default=200.0, ge=0, le=1000,
                       description="AQI PM2.5 µg/m³"),
    wind_speed: float = Query(default=30.0, ge=0, le=200,
                              description="Wind speed km/h"),
    coverage_cap: float = Query(default=2500.0, ge=500, le=10000,
                                description="Coverage cap INR"),
    claims_this_week: int = Query(default=0, ge=0, le=10,
                                  description="Claims filed this week"),
):
    """
    Full engine pipeline via query params.
    Example: /calculate?rainfall=80&aqi=300&wind_speed=55&claims_this_week=1
    """
    risk_r  = calculate_risk(rainfall, aqi, wind_speed)
    trend_r = predict_risk_trend(rainfall, aqi, wind_speed)

    ctx  = ClaimContext(claims_this_week=claims_this_week)
    excl = evaluate_exclusions(ctx)

    plan   = CoveragePlan(coverage_cap=coverage_cap)
    payout = calculate_payout(
        risk_r.risk_score, risk_r.risk_level, plan,
        anomaly_detected=risk_r.anomaly_flag,
        claims_this_period=claims_this_week + 1,
    )
    if excl.is_excluded:
        payout = apply_exclusion_to_payout(
            payout, excl.exclusion_code, excl.is_partial,
            excl.reduction_pct, excl.reason,
        )

    fraud = detect_fraud(
        payout_triggered=payout.payout_triggered,
        risk_score=risk_r.risk_score,
        rainfall=rainfall, aqi=aqi, wind_speed=wind_speed,
        rainfall_score=risk_r.rainfall_score,
        aqi_score=risk_r.aqi_score,
        wind_score=risk_r.wind_score,
        claims_this_week=claims_this_week,
        anomaly_flag=risk_r.anomaly_flag,
    )

    effective = payout.adjusted_net_payout if excl.is_excluded else payout.final_payout
    if fraud.verdict in ("BLOCKED", "SUSPICIOUS"):
        effective = 0.0

    act = payout.actuarial

    return {
        "rainfall": rainfall, "aqi": aqi, "wind_speed": wind_speed,
        "risk_score":     risk_r.risk_score,
        "risk_level":     risk_r.risk_level,
        "primary_hazard": risk_r.primary_hazard,
        "imd_bands": {"rainfall": risk_r.rainfall_band,
                      "aqi": risk_r.aqi_band, "wind_speed": risk_r.wind_band},
        "confidence": {"score": risk_r.confidence, "label": risk_r.confidence_label},
        "risk_trend": {"trend": trend_r.trend, "message": trend_r.message,
                       "eta_hours": trend_r.eta_hours,
                       "contributing_factors": trend_r.contributing_factors,
                       "confidence": trend_r.confidence},
        # v4 AI fields
        "trend":          risk_r.trend,
        "trend_velocity": risk_r.trend_velocity,
        "anomaly_flag":     risk_r.anomaly_flag,
        "anomaly_severity": risk_r.anomaly_severity,
        "predicted_risk_score": risk_r.predicted_risk_score,
        "predicted_risk_level": risk_r.predicted_risk_level,
        "risk_category_reason": risk_r.risk_category_reason,
        "decision_explanation": risk_r.decision_explanation,
        # payout
        "payout_triggered":  payout.payout_triggered,
        "tier_label":        payout.tier_label,
        "payout_percentage": payout.payout_percentage,
        "coverage_cap":      payout.coverage_cap,
        "gross_payout":      payout.gross_payout,
        "platform_fee":      payout.platform_fee,
        "net_payout":        payout.net_payout,
        "risk_loading":      payout.risk_loading,
        "claim_adjustment":  payout.claim_adjustment,
        "final_payout":      payout.final_payout,
        "payout":            effective,
        "exclusion": {
            "is_excluded": excl.is_excluded, "exclusion_code": excl.exclusion_code,
            "reason": excl.reason, "is_partial": excl.is_partial,
            "reduction_pct": excl.reduction_pct,
            "applicable_clauses": excl.applicable_clauses,
        },
        "fraud_check": {
            "raw_score": fraud.raw_score, "fraud_score": fraud.fraud_score,
            "fraud_flag": fraud.fraud_flag, "verdict": fraud.verdict,
            "flag_codes": fraud.flag_codes, "reason": fraud.reason,
            "fraud_explanation": fraud.fraud_explanation,
            "auto_approve": fraud.auto_approve,
            "flags": [{"rule_code": f.rule_code, "weight": f.weight,
                       "description": f.description} for f in fraud.flags],
        },
        "actuarial": {
            "pure_premium":          act.pure_premium           if act else None,
            "loaded_premium":        act.loaded_premium         if act else None,
            "premium_adequacy":      act.premium_adequacy       if act else None,
            "expected_loss_ratio":   act.expected_loss_ratio    if act else None,
            "claims_reserve":        act.claims_reserve         if act else None,
            "expected_weekly_payout":act.expected_weekly_payout if act else None,
            "event_probability":     act.event_probability      if act else None,
            "expected_loss":         act.expected_loss          if act else None,
            "dynamic_premium":       act.dynamic_premium        if act else None,
            "risk_loading":          act.risk_loading           if act else None,
            "claim_adjustment":      act.claim_adjustment       if act else None,
        },
        "payout_explanation": payout.payout_explanation,
        "message": payout.message,
    }