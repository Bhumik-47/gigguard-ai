from fastapi import APIRouter
from backend.models.schemas import RiskResponse
from backend.dependencies.data_service import get_current_environmental_data

router = APIRouter()

@router.get("/risk", response_model=RiskResponse,
         summary="Environmental risk monitoring", tags=["Frontend"])
def risk():
    """Live risk data with trend analysis, anomaly detection, and prediction."""
    return get_current_environmental_data()