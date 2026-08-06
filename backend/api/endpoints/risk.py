from fastapi import APIRouter, Request
from backend.models.schemas import RiskResponse
from backend.dependencies.data_service import get_current_environmental_data
from middleware.rate_limiter import limiter

router = APIRouter()

@router.get("/risk", response_model=RiskResponse,
         summary="Environmental risk monitoring", tags=["Frontend"])
@limiter.limit("30/minute")
def risk(request: Request):
    """Live risk data with trend analysis, anomaly detection, and prediction."""
    return get_current_environmental_data()