from fastapi import APIRouter

router = APIRouter()

@router.get("/", summary="Health check", tags=["Utility"])
def root():
    return {
        "service": "GigGuard AI Backend", "status": "running", "version": "4.0.0",
        "docs": "/docs",
        "endpoints": ["/dashboard", "/risk", "/simulate", "/calculate"],
        "v4_ai_features": [
            "Rolling window (10 observations) risk score memory",
            "Linear regression trend detection: increasing / stable / decreasing",
            "Trend velocity (slope magnitude) for UI sparklines",
            "Z-score anomaly detection per environmental parameter",
            "Predictive risk score (extrapolated 3 steps ahead)",
            "Decision explanation — natural language AI narrative",
            "Dynamic premium pricing: base × (1 + risk_score)",
            "Event probability table: P(disruption | risk_score)",
            "Expected loss calculation: P(event) × coverage_cap",
            "Risk loading factor: base + anomaly surcharge + repeat claim loading",
            "Claim frequency payout tapering: 100% → 80% → 60% → 40%",
            "Fraud pattern memory via rolling buffer correlation",
            "Normalised fraud_score 0.0–1.0 + fraud_flag boolean",
            "7 fraud rules including anomaly correlation + persistent near-threshold",
        ],
    }