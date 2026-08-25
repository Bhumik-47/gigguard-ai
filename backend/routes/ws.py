import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, worker_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[worker_id] = websocket
        logger.info(f"Worker {worker_id} connected via WebSocket")

    def disconnect(self, worker_id: str):
        self.active_connections.pop(worker_id, None)
        logger.info(f"Worker {worker_id} disconnected from WebSocket")

    async def send_update(self, worker_id: str, data: dict):
        ws = self.active_connections.get(worker_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.error(f"Failed to send to {worker_id}: {e}")
                self.disconnect(worker_id)


manager = ConnectionManager()


async def _get_live_status(worker_id: str) -> dict:
    """
    Fetches live environmental and policy status for a worker.
    Replace with real data fetching from your weather service.
    """
    import os
    import requests

    api_key = os.getenv("OPENWEATHERMAP_API_KEY", "")
    city = "Bengaluru"  # In production: look up worker's registered city

    weather_data = {}
    if api_key:
        try:
            resp = requests.get(
                f"http://api.openweathermap.org/data/2.5/weather",
                params={"q": city, "appid": api_key, "units": "metric"},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                weather_data = {
                    "temperature_celsius": data["main"]["temp"],
                    "wind_speed_kmh": data["wind"]["speed"] * 3.6,
                    "rainfall_mm_per_hr": data.get("rain", {}).get("1h", 0),
                    "description": data["weather"][0]["description"],
                }
        except Exception:
            pass

    # Fallback / default values
    if not weather_data:
        weather_data = {
            "temperature_celsius": 28.0,
            "wind_speed_kmh": 15.0,
            "rainfall_mm_per_hr": 0.0,
            "description": "clear sky",
        }

    return {
        "worker_id": worker_id,
        "status": "active",
        "weather": weather_data,
        "risk_level": "LOW",
        "trigger_detected": False,
        "message": "Monitoring active. No triggers detected.",
    }


@router.websocket("/ws/policy-status/{worker_id}")
async def policy_status_ws(websocket: WebSocket, worker_id: str):
    await manager.connect(worker_id, websocket)
    try:
        while True:
            status = await _get_live_status(worker_id)
            await manager.send_update(worker_id, status)
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        manager.disconnect(worker_id)
    except Exception as e:
        logger.error(f"WebSocket error for {worker_id}: {e}")
        manager.disconnect(worker_id)