from backend.models.schemas import DashboardResponse
from backend.dependencies.data_service import get_dashboard_data
from fastapi import APIRouter

router =  APIRouter()

@router.get("/dashboard", response_model=DashboardResponse,
         summary="Worker Dashboard", tags=["Frontend"])
def dashboard():
    """Full dashboard payload including all v4 AI and actuarial fields."""
    return get_dashboard_data()