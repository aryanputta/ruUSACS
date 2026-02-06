"""
Location Share Service - Safety Module
Share live location with friends for safety
Azure Service: Azure Maps
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from enum import Enum
import uuid

router = APIRouter(prefix="/safety/share", tags=["Safety - Location Share"])


class ShareDuration(str, Enum):
    MINUTES_15 = "15_min"
    MINUTES_30 = "30_min"
    HOUR_1 = "1_hour"
    UNTIL_PARKED = "until_parked"
    INDEFINITE = "indefinite"


class LocationShare(BaseModel):
    share_id: str
    user_id: str
    shared_with: List[str]  # User IDs who can see location
    latitude: float
    longitude: float
    last_updated: datetime
    expires_at: Optional[datetime] = None
    duration: ShareDuration
    is_active: bool = True


class ShareLocationInput(BaseModel):
    share_with: List[str]
    duration: ShareDuration = ShareDuration.HOUR_1


# In-memory store
active_shares: dict = {}


@router.get("/active", response_model=List[LocationShare])
async def get_active_shares(user_id: str):
    """Get all active location shares by user"""
    return [s for s in active_shares.values() if s.user_id == user_id and s.is_active]


@router.get("/shared-with-me", response_model=List[LocationShare])
async def get_shared_with_me(user_id: str):
    """Get locations shared with the user"""
    return [s for s in active_shares.values() if user_id in s.shared_with and s.is_active]


@router.post("/start", response_model=LocationShare)
async def start_sharing(user_id: str, input: ShareLocationInput, lat: float, lng: float):
    """Start sharing location with friends"""
    share_id = str(uuid.uuid4())
    
    # Calculate expiry
    duration_map = {
        ShareDuration.MINUTES_15: timedelta(minutes=15),
        ShareDuration.MINUTES_30: timedelta(minutes=30),
        ShareDuration.HOUR_1: timedelta(hours=1),
    }
    expires = None
    if input.duration in duration_map:
        expires = datetime.utcnow() + duration_map[input.duration]
    
    share = LocationShare(
        share_id=share_id,
        user_id=user_id,
        shared_with=input.share_with,
        latitude=lat,
        longitude=lng,
        last_updated=datetime.utcnow(),
        expires_at=expires,
        duration=input.duration
    )
    
    active_shares[share_id] = share
    return share


@router.put("/{share_id}/update")
async def update_location(user_id: str, share_id: str, lat: float, lng: float):
    """Update shared location"""
    if share_id not in active_shares:
        raise HTTPException(status_code=404, detail="Share not found")
    
    share = active_shares[share_id]
    if share.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your share")
    
    share.latitude = lat
    share.longitude = lng
    share.last_updated = datetime.utcnow()
    
    return {"message": "Location updated"}


@router.delete("/{share_id}/stop")
async def stop_sharing(user_id: str, share_id: str):
    """Stop sharing location"""
    if share_id not in active_shares:
        raise HTTPException(status_code=404, detail="Share not found")
    
    share = active_shares[share_id]
    if share.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your share")
    
    share.is_active = False
    return {"message": "Location sharing stopped"}
