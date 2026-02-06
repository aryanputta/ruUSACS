"""
Carpool Service - Sustainability Module
Match with friends/classmates for carpooling
Azure Service: NONE
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date, time
from enum import Enum
import uuid

router = APIRouter(prefix="/sustainability/carpool", tags=["Sustainability - Carpool"])


class CarpoolRole(str, Enum):
    DRIVER = "driver"
    RIDER = "rider"
    FLEXIBLE = "flexible"


class CarpoolStatus(str, Enum):
    OPEN = "open"
    FULL = "full"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CarpoolTrip(BaseModel):
    trip_id: str
    driver_id: str
    driver_name: str
    riders: List[str] = []
    max_riders: int = 3
    pickup_location: str
    destination: str
    departure_date: date
    departure_time: str
    status: CarpoolStatus = CarpoolStatus.OPEN
    recurring: bool = False
    days: Optional[List[str]] = None  # For recurring trips


class CarpoolRequest(BaseModel):
    request_id: str
    user_id: str
    role: CarpoolRole
    pickup_location: str
    destination: str
    preferred_date: date
    preferred_time: str
    flexible_time: bool = True


# In-memory store
trips_db: dict = {}
requests_db: List[CarpoolRequest] = []


@router.get("/trips", response_model=List[CarpoolTrip])
async def get_available_trips(destination: Optional[str] = None):
    """Get available carpool trips"""
    trips = [t for t in trips_db.values() if t.status == CarpoolStatus.OPEN]
    if destination:
        trips = [t for t in trips if destination.lower() in t.destination.lower()]
    return trips


@router.get("/my-trips", response_model=List[CarpoolTrip])
async def get_my_trips(user_id: str):
    """Get user's carpool trips (as driver or rider)"""
    return [t for t in trips_db.values() 
            if t.driver_id == user_id or user_id in t.riders]


@router.post("/trips", response_model=CarpoolTrip)
async def create_trip(user_id: str, pickup_location: str, destination: str,
                      departure_date: date, departure_time: str, max_riders: int = 3):
    """Create a new carpool trip as driver"""
    trip_id = str(uuid.uuid4())
    
    trip = CarpoolTrip(
        trip_id=trip_id,
        driver_id=user_id,
        driver_name=f"User {user_id}",
        pickup_location=pickup_location,
        destination=destination,
        departure_date=departure_date,
        departure_time=departure_time,
        max_riders=max_riders
    )
    
    trips_db[trip_id] = trip
    return trip


@router.post("/trips/{trip_id}/join")
async def join_trip(user_id: str, trip_id: str):
    """Join a carpool trip as rider"""
    if trip_id not in trips_db:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip = trips_db[trip_id]
    
    if trip.status != CarpoolStatus.OPEN:
        raise HTTPException(status_code=400, detail="Trip not available")
    
    if user_id in trip.riders:
        raise HTTPException(status_code=400, detail="Already joined")
    
    if len(trip.riders) >= trip.max_riders:
        raise HTTPException(status_code=400, detail="Trip is full")
    
    trip.riders.append(user_id)
    
    if len(trip.riders) >= trip.max_riders:
        trip.status = CarpoolStatus.FULL
    
    return {"message": "Joined carpool!", "trip": trip}


@router.delete("/trips/{trip_id}/leave")
async def leave_trip(user_id: str, trip_id: str):
    """Leave a carpool trip"""
    if trip_id not in trips_db:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip = trips_db[trip_id]
    
    if user_id not in trip.riders:
        raise HTTPException(status_code=400, detail="Not a rider")
    
    trip.riders.remove(user_id)
    trip.status = CarpoolStatus.OPEN
    
    return {"message": "Left carpool"}


@router.get("/matches")
async def find_carpool_matches(user_id: str, destination: str, date: date):
    """Find matching carpool opportunities"""
    matches = []
    
    # Find trips going to similar destination
    for trip in trips_db.values():
        if (trip.status == CarpoolStatus.OPEN and 
            trip.departure_date == date and
            destination.lower() in trip.destination.lower() and
            trip.driver_id != user_id):
            matches.append({"type": "trip", "data": trip})
    
    # Find riders looking for same destination
    for req in requests_db:
        if (req.preferred_date == date and 
            destination.lower() in req.destination.lower() and
            req.user_id != user_id):
            matches.append({"type": "request", "data": req})
    
    return {"matches": matches, "count": len(matches)}
