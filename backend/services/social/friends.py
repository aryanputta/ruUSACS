"""
Friends Service - Social Module
Manages friend connections, friend list, and friend status
Azure Service: Azure AD B2C
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

router = APIRouter(prefix="/social/friends", tags=["Social - Friends"])


class FriendStatus(str, Enum):
    PARKING = "parking"
    DRIVING = "driving"
    WALKING = "walking"
    PARKED = "parked"
    OFFLINE = "offline"


class Friend(BaseModel):
    user_id: str
    username: str
    display_name: str
    status: FriendStatus = FriendStatus.OFFLINE
    last_seen: Optional[datetime] = None
    location_shared: bool = False


class FriendList(BaseModel):
    friends: List[Friend]
    total_count: int


# In-memory store (replace with database in production)
friends_db: dict = {}


@router.get("/", response_model=FriendList)
async def get_friends(user_id: str):
    """Get all friends for a user"""
    user_friends = friends_db.get(user_id, [])
    return FriendList(friends=user_friends, total_count=len(user_friends))


@router.get("/{friend_id}", response_model=Friend)
async def get_friend(user_id: str, friend_id: str):
    """Get a specific friend's details and status"""
    user_friends = friends_db.get(user_id, [])
    for friend in user_friends:
        if friend.user_id == friend_id:
            return friend
    raise HTTPException(status_code=404, detail="Friend not found")


@router.post("/add")
async def add_friend(user_id: str, friend_id: str):
    """Add a friend connection (after request accepted)"""
    if user_id not in friends_db:
        friends_db[user_id] = []
    
    # Check if already friends
    for friend in friends_db[user_id]:
        if friend.user_id == friend_id:
            raise HTTPException(status_code=400, detail="Already friends")
    
    new_friend = Friend(
        user_id=friend_id,
        username=f"user_{friend_id}",
        display_name=f"User {friend_id}"
    )
    friends_db[user_id].append(new_friend)
    
    return {"message": "Friend added successfully", "friend": new_friend}


@router.delete("/{friend_id}")
async def remove_friend(user_id: str, friend_id: str):
    """Remove a friend connection"""
    if user_id not in friends_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    friends_db[user_id] = [f for f in friends_db[user_id] if f.user_id != friend_id]
    return {"message": "Friend removed successfully"}


@router.put("/{friend_id}/status")
async def update_friend_status(user_id: str, status: FriendStatus):
    """Update current user's status visible to friends"""
    # Broadcast status update to all friends
    return {"message": "Status updated", "status": status}


@router.get("/online")
async def get_online_friends(user_id: str) -> List[Friend]:
    """Get list of friends currently online/active"""
    user_friends = friends_db.get(user_id, [])
    return [f for f in user_friends if f.status != FriendStatus.OFFLINE]
