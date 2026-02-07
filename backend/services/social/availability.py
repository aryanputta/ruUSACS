"""
Availability Service - Friend Coordination
Manages friend availability states and timestamps
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime
from enum import Enum

router = APIRouter(prefix="/social/availability", tags=["Social - Availability"])


class AvailabilityState(str, Enum):
    AVAILABLE = "available"
    ON_CAMPUS = "on_campus"
    LEAVING = "leaving"
    NOT_AVAILABLE = "not_available"


class UserAvailability(BaseModel):
    user_id: str
    state: AvailabilityState
    updated_at: datetime
    expires_at: Optional[datetime] = None
    note: Optional[str] = None


availability_db: Dict[str, UserAvailability] = {}


@router.get("/{user_id}", response_model=UserAvailability)
async def get_availability(user_id: str):
    if user_id not in availability_db:
        return UserAvailability(
            user_id=user_id,
            state=AvailabilityState.NOT_AVAILABLE,
            updated_at=datetime.utcnow()
        )
    return availability_db[user_id]


@router.put("/{user_id}")
async def set_availability(user_id: str, state: AvailabilityState, note: Optional[str] = None):
    availability_db[user_id] = UserAvailability(
        user_id=user_id,
        state=state,
        updated_at=datetime.utcnow(),
        note=note
    )
    return {"message": f"Status set to {state.value}", "availability": availability_db[user_id]}


@router.get("/friends/{user_id}")
async def get_friends_availability(user_id: str):
    # Returns availability of all friends (reads from friends list)
    # For now returns all availability data
    return {"friends": list(availability_db.values())}


@router.get("/leaving/now")
async def get_users_leaving():
    return [a for a in availability_db.values() if a.state == AvailabilityState.LEAVING]
