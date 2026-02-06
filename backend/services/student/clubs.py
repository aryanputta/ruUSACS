"""
Clubs Service - Student Module
Club-based parking groups and coordination
Azure Service: NONE
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

router = APIRouter(prefix="/student/clubs", tags=["Student - Clubs"])


class Club(BaseModel):
    club_id: str
    name: str
    description: Optional[str] = None
    meeting_location: Optional[str] = None
    preferred_lot: Optional[str] = None
    member_ids: List[str] = []
    admin_ids: List[str] = []


class ClubMembership(BaseModel):
    user_id: str
    clubs: List[Club]


# In-memory store
clubs_db: dict = {}
user_clubs_db: dict = {}


@router.get("/", response_model=List[Club])
async def get_user_clubs(user_id: str):
    """Get all clubs user is a member of"""
    return user_clubs_db.get(user_id, [])


@router.get("/all", response_model=List[Club])
async def get_all_clubs():
    """Get all available clubs"""
    return list(clubs_db.values())


@router.get("/{club_id}", response_model=Club)
async def get_club(club_id: str):
    """Get club details"""
    if club_id not in clubs_db:
        raise HTTPException(status_code=404, detail="Club not found")
    return clubs_db[club_id]


@router.post("/", response_model=Club)
async def create_club(user_id: str, name: str, description: Optional[str] = None):
    """Create a new club"""
    club_id = str(uuid.uuid4())
    
    new_club = Club(
        club_id=club_id,
        name=name,
        description=description,
        member_ids=[user_id],
        admin_ids=[user_id]
    )
    
    clubs_db[club_id] = new_club
    
    if user_id not in user_clubs_db:
        user_clubs_db[user_id] = []
    user_clubs_db[user_id].append(new_club)
    
    return new_club


@router.post("/{club_id}/join")
async def join_club(user_id: str, club_id: str):
    """Join a club"""
    if club_id not in clubs_db:
        raise HTTPException(status_code=404, detail="Club not found")
    
    club = clubs_db[club_id]
    
    if user_id in club.member_ids:
        raise HTTPException(status_code=400, detail="Already a member")
    
    club.member_ids.append(user_id)
    
    if user_id not in user_clubs_db:
        user_clubs_db[user_id] = []
    user_clubs_db[user_id].append(club)
    
    return {"message": f"Joined {club.name}"}


@router.delete("/{club_id}/leave")
async def leave_club(user_id: str, club_id: str):
    """Leave a club"""
    if club_id not in clubs_db:
        raise HTTPException(status_code=404, detail="Club not found")
    
    club = clubs_db[club_id]
    
    if user_id not in club.member_ids:
        raise HTTPException(status_code=400, detail="Not a member")
    
    club.member_ids.remove(user_id)
    user_clubs_db[user_id] = [c for c in user_clubs_db.get(user_id, []) if c.club_id != club_id]
    
    return {"message": f"Left {club.name}"}


@router.put("/{club_id}/lot")
async def set_preferred_lot(user_id: str, club_id: str, lot_name: str):
    """Set preferred parking lot for club meetings"""
    if club_id not in clubs_db:
        raise HTTPException(status_code=404, detail="Club not found")
    
    club = clubs_db[club_id]
    
    if user_id not in club.admin_ids:
        raise HTTPException(status_code=403, detail="Only admins can update club settings")
    
    club.preferred_lot = lot_name
    return {"message": f"Preferred lot set to {lot_name}"}


@router.get("/{club_id}/members-parking")
async def get_members_heading_to_meeting(club_id: str):
    """Get club members currently heading to a meeting"""
    if club_id not in clubs_db:
        raise HTTPException(status_code=404, detail="Club not found")
    
    # TODO: Integrate with location/status service
    return {"members_heading": [], "note": "Integration pending"}
