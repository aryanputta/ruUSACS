"""
Walk Sessions Service - Safety Module
"Walk with me" virtual escort feature
Azure Service: Azure Maps
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum
import uuid

router = APIRouter(prefix="/safety/sessions", tags=["Safety - Walk Sessions"])


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    SOS = "sos"


class WalkSession(BaseModel):
    session_id: str
    user_id: str
    watchers: List[str]  # Friends watching the walk
    start_location: dict  # {lat, lng, name}
    destination: dict     # {lat, lng, name}
    started_at: datetime
    expected_duration_min: int
    status: SessionStatus = SessionStatus.ACTIVE
    check_ins: List[datetime] = []
    current_location: Optional[dict] = None


class StartWalkInput(BaseModel):
    watchers: List[str]
    start_location: dict
    destination: dict
    expected_duration_min: int = 15


# In-memory store
sessions_db: dict = {}


@router.get("/active", response_model=Optional[WalkSession])
async def get_active_session(user_id: str):
    """Get user's current active walk session"""
    for session in sessions_db.values():
        if session.user_id == user_id and session.status == SessionStatus.ACTIVE:
            return session
    return None


@router.get("/watching", response_model=List[WalkSession])
async def get_sessions_watching(user_id: str):
    """Get walk sessions user is watching"""
    return [s for s in sessions_db.values() 
            if user_id in s.watchers and s.status == SessionStatus.ACTIVE]


@router.post("/start", response_model=WalkSession)
async def start_walk_session(user_id: str, input: StartWalkInput):
    """Start a walk-with-me session"""
    session_id = str(uuid.uuid4())
    
    session = WalkSession(
        session_id=session_id,
        user_id=user_id,
        watchers=input.watchers,
        start_location=input.start_location,
        destination=input.destination,
        started_at=datetime.utcnow(),
        expected_duration_min=input.expected_duration_min,
        current_location=input.start_location
    )
    
    sessions_db[session_id] = session
    
    # TODO: Notify watchers via Azure Notification Hubs
    
    return session


@router.post("/{session_id}/checkin")
async def check_in(user_id: str, session_id: str, lat: float, lng: float):
    """Check in during walk to confirm safety"""
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions_db[session_id]
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your session")
    
    session.check_ins.append(datetime.utcnow())
    session.current_location = {"lat": lat, "lng": lng}
    
    return {"message": "Checked in", "check_in_count": len(session.check_ins)}


@router.post("/{session_id}/arrived")
async def mark_arrived(user_id: str, session_id: str):
    """Mark that user arrived safely"""
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions_db[session_id]
    session.status = SessionStatus.COMPLETED
    
    # TODO: Notify watchers of safe arrival
    
    return {"message": "Arrived safely! Watchers notified."}


@router.post("/{session_id}/sos")
async def trigger_sos(user_id: str, session_id: str, lat: float, lng: float):
    """Trigger SOS alert to all watchers"""
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions_db[session_id]
    session.status = SessionStatus.SOS
    session.current_location = {"lat": lat, "lng": lng}
    
    # TODO: Send urgent push notification to all watchers
    # TODO: Consider integration with campus security
    
    return {
        "message": "SOS SENT! All watchers alerted with your location.",
        "watchers_notified": session.watchers
    }


@router.delete("/{session_id}/cancel")
async def cancel_session(user_id: str, session_id: str):
    """Cancel a walk session"""
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions_db[session_id]
    session.status = SessionStatus.CANCELLED
    
    return {"message": "Session cancelled"}
