"""
Parking Request Service
Students can post requests for parking spots they need
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from enum import Enum

router = APIRouter(prefix="/trading/requests", tags=["Trading - Requests"])


class RequestUrgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ParkingRequest(BaseModel):
    request_id: str = None
    user_id: str
    needed_date: date
    start_time: str
    end_time: str
    preferred_lots: List[str] = []
    urgency: RequestUrgency = RequestUrgency.MEDIUM
    message: Optional[str] = None
    is_fulfilled: bool = False
    created_at: datetime = None


class RequestResponse(BaseModel):
    response_id: str = None
    request_id: str
    responder_id: str
    spot_offered: Optional[str] = None
    message: str
    created_at: datetime = None


# In-memory storage
requests_db: dict = {}
responses_db: dict = {}


@router.post("/")
async def create_parking_request(request: ParkingRequest):
    """Create a new parking request"""
    request.request_id = f"req_{len(requests_db) + 1}"
    request.created_at = datetime.now()
    requests_db[request.request_id] = request.model_dump()
    return {"message": "Request posted", "request": requests_db[request.request_id]}


@router.get("/")
async def get_all_requests(
    lot: Optional[str] = None,
    date_filter: Optional[date] = None,
    urgency: Optional[RequestUrgency] = None
):
    """Get all open parking requests"""
    open_requests = [r for r in requests_db.values() if not r["is_fulfilled"]]
    
    if lot:
        open_requests = [r for r in open_requests if lot in r.get("preferred_lots", [])]
    if date_filter:
        open_requests = [r for r in open_requests if r["needed_date"] == date_filter.isoformat()]
    if urgency:
        open_requests = [r for r in open_requests if r["urgency"] == urgency]
    
    # Sort by urgency
    urgency_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    open_requests.sort(key=lambda x: urgency_order.get(x["urgency"], 2))
    
    return {"requests": open_requests, "count": len(open_requests)}


@router.get("/my/{user_id}")
async def get_my_requests(user_id: str):
    """Get all requests posted by a user"""
    my_requests = [r for r in requests_db.values() if r["user_id"] == user_id]
    return {"requests": my_requests}


@router.post("/{request_id}/respond")
async def respond_to_request(request_id: str, response: RequestResponse):
    """Respond to a parking request with an offer"""
    if request_id not in requests_db:
        raise HTTPException(status_code=404, detail="Request not found")
    
    response.response_id = f"resp_{len(responses_db) + 1}"
    response.request_id = request_id
    response.created_at = datetime.now()
    responses_db[response.response_id] = response.model_dump()
    
    return {"message": "Response sent", "response": responses_db[response.response_id]}


@router.get("/{request_id}/responses")
async def get_request_responses(request_id: str):
    """Get all responses to a parking request"""
    if request_id not in requests_db:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request_responses = [r for r in responses_db.values() if r["request_id"] == request_id]
    return {"responses": request_responses}


@router.post("/{request_id}/fulfill")
async def fulfill_request(request_id: str, fulfilled_by: str):
    """Mark a parking request as fulfilled"""
    if request_id not in requests_db:
        raise HTTPException(status_code=404, detail="Request not found")
    
    requests_db[request_id]["is_fulfilled"] = True
    requests_db[request_id]["fulfilled_by"] = fulfilled_by
    requests_db[request_id]["fulfilled_at"] = datetime.now().isoformat()
    
    return {"message": "Request marked as fulfilled"}


@router.delete("/{request_id}")
async def cancel_request(request_id: str, user_id: str):
    """Cancel a parking request"""
    if request_id not in requests_db:
        raise HTTPException(status_code=404, detail="Request not found")
    if requests_db[request_id]["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not your request")
    
    del requests_db[request_id]
    return {"message": "Request cancelled"}
