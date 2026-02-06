"""
Parking Spot Trading Service
Students can list, trade, and claim parking spots
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from enum import Enum

router = APIRouter(prefix="/trading/spots", tags=["Trading - Spots"])


class SpotStatus(str, Enum):
    AVAILABLE = "available"
    PENDING = "pending"
    TRADED = "traded"
    EXPIRED = "expired"


class ParkingSpot(BaseModel):
    spot_id: str
    owner_id: str
    lot_name: str
    spot_number: Optional[str] = None
    available_date: date
    start_time: str
    end_time: str
    status: SpotStatus = SpotStatus.AVAILABLE
    created_at: datetime = None


class TradeOffer(BaseModel):
    offer_id: str
    spot_id: str
    from_user_id: str
    to_user_id: str
    message: Optional[str] = None
    status: str = "pending"
    created_at: datetime = None


# In-memory storage
spots_db: dict = {}
offers_db: dict = {}


@router.post("/list")
async def list_parking_spot(spot: ParkingSpot):
    """List a parking spot for trading"""
    spot.created_at = datetime.now()
    spot.spot_id = f"spot_{len(spots_db) + 1}"
    spots_db[spot.spot_id] = spot.model_dump()
    return {"message": "Spot listed successfully", "spot": spots_db[spot.spot_id]}


@router.get("/available")
async def get_available_spots(lot_name: Optional[str] = None, date_filter: Optional[date] = None):
    """Get all available parking spots, optionally filtered by lot or date"""
    available = [s for s in spots_db.values() if s["status"] == SpotStatus.AVAILABLE]
    
    if lot_name:
        available = [s for s in available if s["lot_name"].lower() == lot_name.lower()]
    if date_filter:
        available = [s for s in available if s["available_date"] == date_filter.isoformat()]
    
    return {"spots": available, "count": len(available)}


@router.get("/my-listings/{user_id}")
async def get_my_listings(user_id: str):
    """Get all spots listed by a user"""
    my_spots = [s for s in spots_db.values() if s["owner_id"] == user_id]
    return {"spots": my_spots, "count": len(my_spots)}


@router.post("/offer")
async def make_trade_offer(offer: TradeOffer):
    """Make an offer to trade/claim a parking spot"""
    if offer.spot_id not in spots_db:
        raise HTTPException(status_code=404, detail="Spot not found")
    
    offer.created_at = datetime.now()
    offer.offer_id = f"offer_{len(offers_db) + 1}"
    offers_db[offer.offer_id] = offer.model_dump()
    
    return {"message": "Offer sent", "offer": offers_db[offer.offer_id]}


@router.get("/offers/{user_id}")
async def get_my_offers(user_id: str):
    """Get all trade offers for a user (sent and received)"""
    sent = [o for o in offers_db.values() if o["from_user_id"] == user_id]
    received = [o for o in offers_db.values() if o["to_user_id"] == user_id]
    return {"sent": sent, "received": received}


@router.post("/offers/{offer_id}/accept")
async def accept_offer(offer_id: str):
    """Accept a trade offer"""
    if offer_id not in offers_db:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    offer = offers_db[offer_id]
    offer["status"] = "accepted"
    
    # Update spot status
    spot_id = offer["spot_id"]
    if spot_id in spots_db:
        spots_db[spot_id]["status"] = SpotStatus.TRADED
    
    return {"message": "Offer accepted", "offer": offer}


@router.post("/offers/{offer_id}/decline")
async def decline_offer(offer_id: str):
    """Decline a trade offer"""
    if offer_id not in offers_db:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    offers_db[offer_id]["status"] = "declined"
    return {"message": "Offer declined"}


@router.delete("/{spot_id}")
async def remove_listing(spot_id: str, user_id: str):
    """Remove a parking spot listing"""
    if spot_id not in spots_db:
        raise HTTPException(status_code=404, detail="Spot not found")
    if spots_db[spot_id]["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not your listing")
    
    del spots_db[spot_id]
    return {"message": "Listing removed"}
