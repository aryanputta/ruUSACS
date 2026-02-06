"""
Metrics Service - Sustainability Module
Track CO₂ saved, trips shared, environmental impact
Azure Service: Azure Application Insights
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from enum import Enum

router = APIRouter(prefix="/sustainability/metrics", tags=["Sustainability - Metrics"])


class MetricType(str, Enum):
    CO2_SAVED = "co2_saved"
    TRIPS_SHARED = "trips_shared"
    MILES_CARPOOLED = "miles_carpooled"
    SPOTS_SHARED = "spots_shared"
    WALKING_TRIPS = "walking_trips"


class UserMetrics(BaseModel):
    user_id: str
    co2_saved_kg: float = 0.0
    trips_shared: int = 0
    miles_carpooled: float = 0.0
    spots_shared: int = 0
    trees_equivalent: float = 0.0  # CO2 absorbed by trees equivalent
    rank_percentile: int = 50


class MetricEntry(BaseModel):
    entry_id: str
    user_id: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    description: Optional[str] = None


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    username: str
    co2_saved_kg: float


# In-memory store
metrics_db: dict = {}
entries_db: List[MetricEntry] = []

# Average CO2 per mile driven (in kg)
CO2_PER_MILE = 0.404


@router.get("/", response_model=UserMetrics)
async def get_user_metrics(user_id: str):
    """Get user's sustainability metrics"""
    if user_id not in metrics_db:
        metrics_db[user_id] = UserMetrics(user_id=user_id)
    return metrics_db[user_id]


@router.post("/log-carpool")
async def log_carpool_trip(user_id: str, miles: float, riders: int):
    """Log a completed carpool trip"""
    if user_id not in metrics_db:
        metrics_db[user_id] = UserMetrics(user_id=user_id)
    
    metrics = metrics_db[user_id]
    
    # Calculate CO2 saved (each rider saves a full trip)
    co2_saved = miles * CO2_PER_MILE * riders
    
    metrics.co2_saved_kg += co2_saved
    metrics.trips_shared += 1
    metrics.miles_carpooled += miles
    metrics.trees_equivalent = metrics.co2_saved_kg / 21.77  # kg CO2 per tree per year
    
    # TODO: Log to Azure Application Insights
    
    return {
        "message": "Carpool logged!",
        "co2_saved": co2_saved,
        "total_co2_saved": metrics.co2_saved_kg
    }


@router.post("/log-spot-share")
async def log_spot_share(user_id: str):
    """Log when user shares a parking spot"""
    if user_id not in metrics_db:
        metrics_db[user_id] = UserMetrics(user_id=user_id)
    
    metrics_db[user_id].spots_shared += 1
    
    # Each spot share prevents ~0.5 miles of circling (estimate)
    metrics_db[user_id].co2_saved_kg += 0.5 * CO2_PER_MILE
    
    return {"message": "Spot share logged!", "total_shares": metrics_db[user_id].spots_shared}


@router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(limit: int = 10):
    """Get sustainability leaderboard"""
    sorted_users = sorted(
        metrics_db.values(), 
        key=lambda m: m.co2_saved_kg, 
        reverse=True
    )[:limit]
    
    return [
        LeaderboardEntry(
            rank=i + 1,
            user_id=m.user_id,
            username=f"User {m.user_id}",
            co2_saved_kg=m.co2_saved_kg
        )
        for i, m in enumerate(sorted_users)
    ]


@router.get("/campus-total")
async def get_campus_total():
    """Get total campus-wide sustainability impact"""
    total_co2 = sum(m.co2_saved_kg for m in metrics_db.values())
    total_trips = sum(m.trips_shared for m in metrics_db.values())
    total_spots = sum(m.spots_shared for m in metrics_db.values())
    
    return {
        "total_co2_saved_kg": total_co2,
        "total_trips_shared": total_trips,
        "total_spots_shared": total_spots,
        "trees_equivalent": total_co2 / 21.77,
        "active_users": len(metrics_db)
    }
