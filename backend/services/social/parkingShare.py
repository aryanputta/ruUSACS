"""
Parking Share Service - Friend Coordination
Social parking coordination signals - allows spot sharing only when overlap exists
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum
import uuid

router = APIRouter(prefix="/social/parking-share", tags=["Social - Parking Share"])


class ShareStatus(str, Enum):
    OFFERED = "offered"
    CLAIMED = "claimed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SpotShare(BaseModel):
    share_id: str
    offerer_id: str
    claimer_id: Optional[str] = None
    status: ShareStatus = ShareStatus.OFFERED
    created_at: datetime
    claimed_at: Optional[datetime] = None


spot_shares: dict = {}


# Import overlap checker
from .overlap import check_overlap, OverlapType


@router.post("/offer")
async def offer_spot(user_id: str, to_friend_id: Optional[str] = None):
    share_id = str(uuid.uuid4())
    
    spot_shares[share_id] = SpotShare(
        share_id=share_id,
        offerer_id=user_id,
        created_at=datetime.utcnow()
    )
    
    return {"message": "Spot offered", "share_id": share_id}


@router.post("/claim/{share_id}")
async def claim_spot(share_id: str, user_id: str):
    if share_id not in spot_shares:
        raise HTTPException(status_code=404, detail="Share not found")
    
    share = spot_shares[share_id]
    
    if share.status != ShareStatus.OFFERED:
        raise HTTPException(status_code=400, detail="Spot no longer available")
    
    # Check overlap exists
    overlap = await check_overlap(user_id, share.offerer_id)
    if not overlap.can_share_spot:
        raise HTTPException(status_code=400, detail="No availability overlap - cannot claim spot")
    
    share.claimer_id = user_id
    share.status = ShareStatus.CLAIMED
    share.claimed_at = datetime.utcnow()
    
    return {"message": "Spot claimed!", "share": share}


@router.get("/available")
async def get_available_shares(user_id: str):
    available = []
    for share in spot_shares.values():
        if share.status == ShareStatus.OFFERED and share.offerer_id != user_id:
            overlap = await check_overlap(user_id, share.offerer_id)
            if overlap.can_share_spot:
                available.append(share)
    return available


@router.delete("/{share_id}")
async def cancel_share(share_id: str, user_id: str):
    if share_id not in spot_shares:
        raise HTTPException(status_code=404, detail="Share not found")
    
    share = spot_shares[share_id]
    if share.offerer_id != user_id:
        raise HTTPException(status_code=403, detail="Not your share")
    
    share.status = ShareStatus.CANCELLED
    return {"message": "Share cancelled"}
