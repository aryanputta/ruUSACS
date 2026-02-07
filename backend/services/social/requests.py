"""
Friend Requests Service - Social Module
Handles sending, accepting, and rejecting friend requests
Azure Service: Azure Notification Hubs
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum
import uuid

router = APIRouter(prefix="/social/requests", tags=["Social - Requests"])


class RequestStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class FriendRequest(BaseModel):
    request_id: str
    from_user_id: str
    from_username: str
    to_user_id: str
    to_username: str
    status: RequestStatus = RequestStatus.PENDING
    created_at: datetime
    message: Optional[str] = None


class SendRequestInput(BaseModel):
    to_user_id: str
    message: Optional[str] = None


# In-memory store (replace with database in production)
requests_db: List[FriendRequest] = []


@router.get("/incoming", response_model=List[FriendRequest])
async def get_incoming_requests(user_id: str):
    """Get all pending incoming friend requests"""
    return [r for r in requests_db 
            if r.to_user_id == user_id and r.status == RequestStatus.PENDING]


@router.get("/outgoing", response_model=List[FriendRequest])
async def get_outgoing_requests(user_id: str):
    """Get all pending outgoing friend requests"""
    return [r for r in requests_db 
            if r.from_user_id == user_id and r.status == RequestStatus.PENDING]


@router.post("/send", response_model=FriendRequest)
async def send_friend_request(user_id: str, request_data: SendRequestInput):
    """Send a friend request to another user"""
    # Check for existing pending request
    for r in requests_db:
        if (r.from_user_id == user_id and r.to_user_id == request_data.to_user_id 
            and r.status == RequestStatus.PENDING):
            raise HTTPException(status_code=400, detail="Request already pending")
    
    new_request = FriendRequest(
        request_id=str(uuid.uuid4()),
        from_user_id=user_id,
        from_username=f"user_{user_id}",
        to_user_id=request_data.to_user_id,
        to_username=f"user_{request_data.to_user_id}",
        created_at=datetime.utcnow(),
        message=request_data.message
    )
    requests_db.append(new_request)
    
    # TODO: Send push notification via Azure Notification Hubs
    # await send_push_notification(request_data.to_user_id, "New friend request!")
    
    return new_request


@router.post("/{request_id}/accept")
async def accept_friend_request(user_id: str, request_id: str):
    """Accept a pending friend request"""
    for r in requests_db:
        if r.request_id == request_id and r.to_user_id == user_id:
            if r.status != RequestStatus.PENDING:
                raise HTTPException(status_code=400, detail="Request not pending")
            r.status = RequestStatus.ACCEPTED
            
            # TODO: Create mutual friend connection
            # TODO: Send notification to requester
            
            return {"message": "Friend request accepted", "request": r}
    
    raise HTTPException(status_code=404, detail="Request not found")


@router.post("/{request_id}/reject")
async def reject_friend_request(user_id: str, request_id: str):
    """Reject a pending friend request"""
    for r in requests_db:
        if r.request_id == request_id and r.to_user_id == user_id:
            if r.status != RequestStatus.PENDING:
                raise HTTPException(status_code=400, detail="Request not pending")
            r.status = RequestStatus.REJECTED
            return {"message": "Friend request rejected"}
    
    raise HTTPException(status_code=404, detail="Request not found")


@router.delete("/{request_id}/cancel")
async def cancel_friend_request(user_id: str, request_id: str):
    """Cancel an outgoing friend request"""
    for r in requests_db:
        if r.request_id == request_id and r.from_user_id == user_id:
            if r.status != RequestStatus.PENDING:
                raise HTTPException(status_code=400, detail="Request not pending")
            r.status = RequestStatus.CANCELLED
            return {"message": "Friend request cancelled"}
    
    raise HTTPException(status_code=404, detail="Request not found")
