# backend/data/pilot_zones.py
from dataclasses import dataclass
from typing import List
import math

@dataclass
class PolicyZone:
    zone_id: str
    city_name: str
    center_lat: float
    center_lon: float
    radius_km: float
    display_name: str
    weather_station_lat: float
    weather_station_lon: float

PILOT_ZONES: List[PolicyZone] = [
    # Mumbai
    PolicyZone("mum-andheri-w",   "Mumbai",    19.1197, 72.8468, 3.0, "Andheri West, Mumbai",       19.1197, 72.8468),
    PolicyZone("mum-bandra",      "Mumbai",    19.0596, 72.8295, 3.0, "Bandra, Mumbai",             19.0596, 72.8295),
    PolicyZone("mum-thane",       "Mumbai",    19.2183, 72.9781, 4.0, "Thane, Mumbai",              19.2183, 72.9781),
    # Delhi
    PolicyZone("del-connaught",   "Delhi",     28.6315, 77.2167, 4.0, "Connaught Place, Delhi",     28.6315, 77.2167),
    PolicyZone("del-dwarka",      "Delhi",     28.5921, 77.0460, 4.0, "Dwarka, Delhi",              28.5921, 77.0460),
    PolicyZone("del-rohini",      "Delhi",     28.7041, 77.1025, 3.5, "Rohini, Delhi",              28.7041, 77.1025),
    # Bangalore
    PolicyZone("blr-koramangala", "Bangalore", 12.9352, 77.6245, 3.0, "Koramangala, Bangalore",     12.9352, 77.6245),
    PolicyZone("blr-whitefield",  "Bangalore", 12.9698, 77.7499, 4.0, "Whitefield, Bangalore",      12.9698, 77.7499),
    PolicyZone("blr-indiranagar", "Bangalore", 12.9784, 77.6408, 2.5, "Indiranagar, Bangalore",     12.9784, 77.6408),
    # Hyderabad
    PolicyZone("hyd-hitech",      "Hyderabad", 17.4435, 78.3772, 4.0, "HITEC City, Hyderabad",      17.4435, 78.3772),
]

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points in kilometres."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def find_nearest_zone(lat: float, lon: float) -> PolicyZone:
    return min(PILOT_ZONES, key=lambda z: haversine_km(lat, lon, z.center_lat, z.center_lon))

def zones_by_city() -> dict:
    result = {}
    for z in PILOT_ZONES:
        result.setdefault(z.city_name, []).append(z)
    return result