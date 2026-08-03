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

from fastapi import FastAPI, APIRouter, Depends
from backend.api.endpoints import dashboard, calculate, risk, simulate, root, monitoring
from backend.middleware.auth import verify_firebase_token
from backend.data.pilot_zones import PILOT_ZONES, find_nearest_zone, zones_by_city

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="GigGuard AI — Backend API",
    description=(
        "Parametric insurance for gig workers. "
        "v4: Rolling-window trend detection · Z-score anomaly detection · "
        "Predictive risk scoring · Dynamic premium pricing · "
        "Risk-loaded payouts · Fraud intelligence with pattern memory. "
        "Enhanced with load balancing, caching, and performance monitoring."
    ),
    version="4.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

from backend.core.config import configure_middleware

configure_middleware(app)

# ---------------------------------------------------------------------------
# API Router with Firebase Authentication Protection
# ---------------------------------------------------------------------------

api_router = APIRouter()

# Public routers (no authentication required)
api_router.include_router(dashboard.router)
api_router.include_router(root.router)          # contains /health, /environment
api_router.include_router(monitoring.router)

# Protected routers – require valid Firebase token
api_router.include_router(
    simulate.router,
    dependencies=[Depends(verify_firebase_token)]
)
api_router.include_router(
    risk.router,
    dependencies=[Depends(verify_firebase_token)]
)
api_router.include_router(
    calculate.router,
    dependencies=[Depends(verify_firebase_token)]
)

# ---------------------------------------------------------------------------
# Public Pilot Zone Endpoints
# ---------------------------------------------------------------------------

@api_router.get("/api/zones")
def list_zones():
    """Returns all pilot zones grouped by city."""
    grouped = zones_by_city()
    return {
        city: [
            {
                "zoneId": z.zone_id,
                "displayName": z.display_name,
                "centerLat": z.center_lat,
                "centerLon": z.center_lon,
                "radiusKm": z.radius_km,
            }
            for z in zones
        ]
        for city, zones in grouped.items()
    }

@api_router.get("/api/zones/nearest")
def nearest_zone(lat: float, lon: float):
    """Returns the nearest pilot zone for given coordinates."""
    zone = find_nearest_zone(lat, lon)
    return {
        "zoneId": zone.zone_id,
        "displayName": zone.display_name,
        "cityName": zone.city_name,
        "centerLat": zone.center_lat,
        "centerLon": zone.center_lon,
        "radiusKm": zone.radius_km,
    }

app.include_router(api_router)
