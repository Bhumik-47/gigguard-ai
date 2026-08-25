from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Literal, Optional
from datetime import datetime, timedelta
import random

router = APIRouter(prefix="/api/claims", tags=["claims"])


class WeatherSnapshot(BaseModel):
    temperature_celsius: float
    rainfall_mm_per_hr: float
    aqi_pm25: float


class Claim(BaseModel):
    claim_id: str
    worker_id: str
    policy_id: str
    triggered_at: str
    trigger_reasons: List[str]
    weather_snapshot: WeatherSnapshot
    payout_amount_inr: float
    payout_status: Literal["processed", "pending", "failed"]


def _mock_claims_for_worker(worker_id: str, limit: int) -> List[dict]:
    """
    Returns mock claim records. Replace with Firestore fetch in production:
    db.collection('claims').where('worker_id', '==', worker_id).limit(limit).get()
    """
    statuses = ["processed", "processed", "processed", "pending", "failed"]
    reasons_pool = [
        ["Heavy rainfall (>15mm/hr)", "High wind speed"],
        ["AQI PM2.5 > 150 (Unhealthy)"],
        ["Extreme heat (>40°C)", "AQI elevated"],
        ["Rainfall threshold breached"],
    ]

    claims = []
    for i in range(min(limit, 5)):
        status = statuses[i % len(statuses)]
        reasons = reasons_pool[i % len(reasons_pool)]
        claims.append({
            "claim_id": f"CLM-{worker_id[:4].upper()}-{1000 + i}",
            "worker_id": worker_id,
            "policy_id": f"POL-{worker_id[:4].upper()}-{500 + i}",
            "triggered_at": (datetime.now() - timedelta(days=i * 7)).isoformat(),
            "trigger_reasons": reasons,
            "weather_snapshot": {
                "temperature_celsius": round(28 + i * 2.5, 1),
                "rainfall_mm_per_hr": round(5 + i * 4.0, 1),
                "aqi_pm25": round(80 + i * 25, 1),
            },
            "payout_amount_inr": round(120 + i * 80, 2) if status == "processed" else 0.0,
            "payout_status": status,
        })
    return claims


@router.get("/history/{worker_id}", response_model=dict)
async def get_claim_history(
    worker_id: str,
    limit: int = Query(default=20, ge=1, le=100),
):
    """
    Returns paginated claim history for a worker.
    Each record includes policy_id, trigger_event, weather_snapshot,
    payout_amount, payout_status, and timestamps.
    """
    if not worker_id.strip():
        raise HTTPException(status_code=400, detail="worker_id cannot be blank")

    claims = _mock_claims_for_worker(worker_id, limit)
    total_paid = sum(c["payout_amount_inr"] for c in claims if c["payout_status"] == "processed")

    return {
        "worker_id": worker_id,
        "claims": claims,
        "total": len(claims),
        "total_lifetime_payout_inr": round(total_paid, 2),
    }