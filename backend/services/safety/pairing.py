"""
Pairing Service - Safety
Pairs friends who are leaving around the same time for safety
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from enum import Enum
import uuid

router = APIRouter(prefix="/safety/pairing", tags=["Safety - Pairing"])


class PairingStatus(str, Enum):
    SUGGESTED = "suggested"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class SafetyPairing(BaseModel):
    pairing_id: str
    user_a: str
    user_b: str
    status: PairingStatus = PairingStatus.SUGGESTED
    created_at: datetime
    expires_at: datetime
    accepted_by: List[str] = []


pairings_db: dict = {}


# Import availability
from ..social.availability import availability_db, AvailabilityState


@router.get("/suggestions/{user_id}")
async def get_pairing_suggestions(user_id: str, time_window_minutes: int = 30):
    suggestions = []
    user_avail = availability_db.get(user_id)
    
    if not user_avail or user_avail.state != AvailabilityState.LEAVING:
        return {"suggestions": [], "message": "Set status to LEAVING to get pairing suggestions"}
    
    for friend_id, friend_avail in availability_db.items():
        if friend_id == user_id:
            continue
            
        if friend_avail.state == AvailabilityState.LEAVING:
            time_diff = abs((user_avail.updated_at - friend_avail.updated_at).total_seconds() / 60)
            if time_diff <= time_window_minutes:
                suggestions.append({
                    "friend_id": friend_id,
                    "their_update": friend_avail.updated_at,
                    "time_diff_minutes": round(time_diff)
                })
    
    return {"suggestions": suggestions}


@router.post("/create/{friend_id}")
async def create_pairing(user_id: str, friend_id: str):
    pairing_id = str(uuid.uuid4())
    
    pairing = SafetyPairing(
        pairing_id=pairing_id,
        user_a=user_id,
        user_b=friend_id,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=1),
        accepted_by=[user_id]
    )
    
    pairings_db[pairing_id] = pairing
    return {"message": "Pairing created, waiting for friend to accept", "pairing": pairing}


@router.post("/accept/{pairing_id}")
async def accept_pairing(pairing_id: str, user_id: str):
    if pairing_id not in pairings_db:
        return {"error": "Pairing not found"}
    
    pairing = pairings_db[pairing_id]
    
    if user_id not in [pairing.user_a, pairing.user_b]:
        return {"error": "Not part of this pairing"}
    
    if user_id not in pairing.accepted_by:
        pairing.accepted_by.append(user_id)
    
    if len(pairing.accepted_by) == 2:
        pairing.status = PairingStatus.ACCEPTED
        return {"message": "Pairing confirmed! Walk together safely.", "pairing": pairing}
    
    return {"message": "Waiting for other person to accept", "pairing": pairing}


@router.get("/active/{user_id}")
async def get_active_pairings(user_id: str):
    active = []
    now = datetime.utcnow()
    
    for pairing in pairings_db.values():
        if user_id in [pairing.user_a, pairing.user_b]:
            if pairing.status == PairingStatus.ACCEPTED and pairing.expires_at > now:
                active.append(pairing)
    
    return active


@router.delete("/{pairing_id}")
async def decline_pairing(pairing_id: str, user_id: str):
    if pairing_id in pairings_db:
        pairings_db[pairing_id].status = PairingStatus.DECLINED
    return {"message": "Pairing declined"}
