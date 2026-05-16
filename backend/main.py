"""
main.py
-------
GigGuard AI — FastAPI Backend  (v4 — Hackathon AI Layer)

All v3 endpoints are preserved and backward-compatible.
Pydantic models updated for v4 fields.

New fields in v4 responses
---------------------------
  trend / trend_velocity / slope / r_squared  — regression-based trend
  anomaly_flag / anomaly_severity / anomaly_details / max_z_score
  predicted_risk_score / predicted_risk_level
  risk_category_reason / decision_explanation
  risk_loading / claim_adjustment / final_payout / payout_explanation
  actuarial.event_probability / expected_loss / dynamic_premium
  fraud_check.fraud_score (0-1) / fraud_flag (bool) / fraud_explanation

Run:
  uvicorn backend.main:app --reload
"""

from fastapi import FastAPI,APIRouter
from .api.endpoints import dashboard,calculate,risk,simulate,root


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="GigGuard AI — Backend API",
    description=(
        "Parametric insurance for gig workers. "
        "v4: Rolling-window trend detection · Z-score anomaly detection · "
        "Predictive risk scoring · Dynamic premium pricing · "
        "Risk-loaded payouts · Fraud intelligence with pattern memory."
    ),
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

from backend.core.config import configure_middleware

configure_middleware(app)


api_router = APIRouter()
api_router.include_router(dashboard.router)
api_router.include_router(simulate.router)
api_router.include_router(risk.router)
api_router.include_router(calculate.router)
api_router.include_router(root.router)

    
app.include_router(api_router)