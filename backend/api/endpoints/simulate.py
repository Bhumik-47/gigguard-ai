from fastapi import APIRouter
from backend.models.schemas import SimulateResponse
from backend.dependencies.data_service import get_simulated_event

router = APIRouter()

@router.get("/simulate", response_model=SimulateResponse,
         summary="Simulated disruption event", tags=["Frontend"])
def simulate():
    """Random scenario — 60% disruption / 20% medium / 20% calm."""
    return get_simulated_event()