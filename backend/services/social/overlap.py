"""
Overlap Service - Friend Coordination
Detects overlap between friends based on availability + time window
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from enum import Enum

router = APIRouter(prefix="/social/overlap", tags=["Social - Overlap"])


class OverlapType(str, Enum):
    BOTH_ON_CAMPUS = "both_on_campus"
    BOTH_LEAVING = "both_leaving"
    ONE_LEAVING = "one_leaving"
    NO_OVERLAP = "no_overlap"


class OverlapResult(BaseModel):
    user_a: str
    user_b: str
    overlap_type: OverlapType
    time_window_minutes: int
    can_share_spot: bool
    can_walk_together: bool


class FriendOverlap(BaseModel):
    friend_id: str
    overlap_type: OverlapType
    their_state: str
    updated_at: datetime


# Import availability from sibling module
from .availability import availability_db, AvailabilityState


@router.get("/check/{user_id}/{friend_id}", response_model=OverlapResult)
async def check_overlap(user_id: str, friend_id: str, time_window_minutes: int = 30):
    user_avail = availability_db.get(user_id)
    friend_avail = availability_db.get(friend_id)
    
    if not user_avail or not friend_avail:
        return OverlapResult(
            user_a=user_id,
            user_b=friend_id,
            overlap_type=OverlapType.NO_OVERLAP,
            time_window_minutes=time_window_minutes,
            can_share_spot=False,
            can_walk_together=False
        )
    
    # Check time window
    time_diff = abs((user_avail.updated_at - friend_avail.updated_at).total_seconds() / 60)
    within_window = time_diff <= time_window_minutes
    
    # Determine overlap type
    if user_avail.state == AvailabilityState.LEAVING and friend_avail.state == AvailabilityState.LEAVING:
        overlap_type = OverlapType.BOTH_LEAVING
        can_share = True
        can_walk = within_window
    elif user_avail.state == AvailabilityState.ON_CAMPUS and friend_avail.state == AvailabilityState.ON_CAMPUS:
        overlap_type = OverlapType.BOTH_ON_CAMPUS
        can_share = False
        can_walk = False
    elif user_avail.state == AvailabilityState.LEAVING or friend_avail.state == AvailabilityState.LEAVING:
        overlap_type = OverlapType.ONE_LEAVING
        can_share = within_window
        can_walk = False
    else:
        overlap_type = OverlapType.NO_OVERLAP
        can_share = False
        can_walk = False
    
    return OverlapResult(
        user_a=user_id,
        user_b=friend_id,
        overlap_type=overlap_type,
        time_window_minutes=time_window_minutes,
        can_share_spot=can_share,
        can_walk_together=can_walk
    )


@router.get("/friends/{user_id}", response_model=List[FriendOverlap])
async def get_all_friend_overlaps(user_id: str):
    overlaps = []
    user_avail = availability_db.get(user_id)
    
    if not user_avail:
        return []
    
    for friend_id, friend_avail in availability_db.items():
        if friend_id != user_id:
            result = await check_overlap(user_id, friend_id)
            if result.overlap_type != OverlapType.NO_OVERLAP:
                overlaps.append(FriendOverlap(
                    friend_id=friend_id,
                    overlap_type=result.overlap_type,
                    their_state=friend_avail.state.value,
                    updated_at=friend_avail.updated_at
                ))
    
    return overlaps
