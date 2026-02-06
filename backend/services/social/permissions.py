"""
Permissions Service - Social Module
Controls who can see location, send requests, view parking status
Azure Service: NONE
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum

router = APIRouter(prefix="/social/permissions", tags=["Social - Permissions"])


class PermissionLevel(str, Enum):
    EVERYONE = "everyone"
    FRIENDS = "friends"
    GROUPS = "groups"
    SPECIFIC = "specific"
    NOBODY = "nobody"


class PermissionType(str, Enum):
    VIEW_LOCATION = "view_location"
    VIEW_STATUS = "view_status"
    SEND_REQUESTS = "send_requests"
    SEND_MESSAGES = "send_messages"
    VIEW_SCHEDULE = "view_schedule"
    CARPOOL_INVITES = "carpool_invites"


class UserPermissions(BaseModel):
    user_id: str
    view_location: PermissionLevel = PermissionLevel.FRIENDS
    view_status: PermissionLevel = PermissionLevel.FRIENDS
    send_requests: PermissionLevel = PermissionLevel.EVERYONE
    send_messages: PermissionLevel = PermissionLevel.FRIENDS
    view_schedule: PermissionLevel = PermissionLevel.FRIENDS
    carpool_invites: PermissionLevel = PermissionLevel.FRIENDS
    blocked_users: List[str] = []
    allowed_users: Dict[PermissionType, List[str]] = {}


class UpdatePermissionInput(BaseModel):
    permission_type: PermissionType
    level: PermissionLevel
    specific_users: Optional[List[str]] = None


# In-memory store
permissions_db: Dict[str, UserPermissions] = {}


def get_user_permissions(user_id: str) -> UserPermissions:
    """Get or create user permissions"""
    if user_id not in permissions_db:
        permissions_db[user_id] = UserPermissions(user_id=user_id)
    return permissions_db[user_id]


@router.get("/", response_model=UserPermissions)
async def get_permissions(user_id: str):
    """Get all permissions for a user"""
    return get_user_permissions(user_id)


@router.put("/")
async def update_permission(user_id: str, update: UpdatePermissionInput):
    """Update a specific permission"""
    perms = get_user_permissions(user_id)
    
    setattr(perms, update.permission_type.value, update.level)
    
    if update.level == PermissionLevel.SPECIFIC and update.specific_users:
        perms.allowed_users[update.permission_type] = update.specific_users
    
    return {"message": "Permission updated", "permissions": perms}


@router.post("/block/{blocked_user_id}")
async def block_user(user_id: str, blocked_user_id: str):
    """Block a user from all interactions"""
    perms = get_user_permissions(user_id)
    
    if blocked_user_id not in perms.blocked_users:
        perms.blocked_users.append(blocked_user_id)
    
    return {"message": f"User {blocked_user_id} blocked"}


@router.delete("/unblock/{blocked_user_id}")
async def unblock_user(user_id: str, blocked_user_id: str):
    """Unblock a previously blocked user"""
    perms = get_user_permissions(user_id)
    
    if blocked_user_id in perms.blocked_users:
        perms.blocked_users.remove(blocked_user_id)
    
    return {"message": f"User {blocked_user_id} unblocked"}


@router.get("/check/{requester_id}/{permission_type}")
async def check_permission(user_id: str, requester_id: str, permission_type: PermissionType):
    """Check if a requester has a specific permission for a user"""
    perms = get_user_permissions(user_id)
    
    # Check if blocked
    if requester_id in perms.blocked_users:
        return {"allowed": False, "reason": "User is blocked"}
    
    level = getattr(perms, permission_type.value)
    
    if level == PermissionLevel.EVERYONE:
        return {"allowed": True}
    elif level == PermissionLevel.NOBODY:
        return {"allowed": False, "reason": "Permission denied to all"}
    elif level == PermissionLevel.SPECIFIC:
        allowed = requester_id in perms.allowed_users.get(permission_type, [])
        return {"allowed": allowed}
    elif level == PermissionLevel.FRIENDS:
        # TODO: Check if requester is a friend
        return {"allowed": True, "note": "Friend check pending"}
    elif level == PermissionLevel.GROUPS:
        # TODO: Check if requester is in same group
        return {"allowed": True, "note": "Group check pending"}
    
    return {"allowed": False}
