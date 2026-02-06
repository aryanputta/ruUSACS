"""
Groups Service - Social Module
Manages parking groups (roommates, study groups, clubs)
Azure Service: NONE
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum
import uuid

router = APIRouter(prefix="/social/groups", tags=["Social - Groups"])


class GroupType(str, Enum):
    ROOMMATES = "roommates"
    STUDY_GROUP = "study_group"
    CLUB = "club"
    CLASS = "class"
    CUSTOM = "custom"


class GroupMember(BaseModel):
    user_id: str
    username: str
    role: str = "member"  # admin, member
    joined_at: datetime


class ParkingGroup(BaseModel):
    group_id: str
    name: str
    group_type: GroupType
    description: Optional[str] = None
    members: List[GroupMember]
    created_by: str
    created_at: datetime
    max_members: int = 20


class CreateGroupInput(BaseModel):
    name: str
    group_type: GroupType
    description: Optional[str] = None
    max_members: int = 20


# In-memory store
groups_db: dict = {}


@router.get("/", response_model=List[ParkingGroup])
async def get_user_groups(user_id: str):
    """Get all groups the user belongs to"""
    user_groups = []
    for group in groups_db.values():
        if any(m.user_id == user_id for m in group.members):
            user_groups.append(group)
    return user_groups


@router.get("/{group_id}", response_model=ParkingGroup)
async def get_group(group_id: str):
    """Get group details"""
    if group_id not in groups_db:
        raise HTTPException(status_code=404, detail="Group not found")
    return groups_db[group_id]


@router.post("/", response_model=ParkingGroup)
async def create_group(user_id: str, group_data: CreateGroupInput):
    """Create a new parking group"""
    group_id = str(uuid.uuid4())
    
    new_group = ParkingGroup(
        group_id=group_id,
        name=group_data.name,
        group_type=group_data.group_type,
        description=group_data.description,
        members=[GroupMember(
            user_id=user_id,
            username=f"user_{user_id}",
            role="admin",
            joined_at=datetime.utcnow()
        )],
        created_by=user_id,
        created_at=datetime.utcnow(),
        max_members=group_data.max_members
    )
    
    groups_db[group_id] = new_group
    return new_group


@router.post("/{group_id}/join")
async def join_group(user_id: str, group_id: str):
    """Join an existing group"""
    if group_id not in groups_db:
        raise HTTPException(status_code=404, detail="Group not found")
    
    group = groups_db[group_id]
    
    if len(group.members) >= group.max_members:
        raise HTTPException(status_code=400, detail="Group is full")
    
    if any(m.user_id == user_id for m in group.members):
        raise HTTPException(status_code=400, detail="Already a member")
    
    group.members.append(GroupMember(
        user_id=user_id,
        username=f"user_{user_id}",
        role="member",
        joined_at=datetime.utcnow()
    ))
    
    return {"message": "Joined group successfully"}


@router.delete("/{group_id}/leave")
async def leave_group(user_id: str, group_id: str):
    """Leave a group"""
    if group_id not in groups_db:
        raise HTTPException(status_code=404, detail="Group not found")
    
    group = groups_db[group_id]
    group.members = [m for m in group.members if m.user_id != user_id]
    
    # Delete group if no members left
    if len(group.members) == 0:
        del groups_db[group_id]
        return {"message": "Left group and group deleted (no members remaining)"}
    
    return {"message": "Left group successfully"}


@router.get("/{group_id}/members", response_model=List[GroupMember])
async def get_group_members(group_id: str):
    """Get all members of a group"""
    if group_id not in groups_db:
        raise HTTPException(status_code=404, detail="Group not found")
    return groups_db[group_id].members
