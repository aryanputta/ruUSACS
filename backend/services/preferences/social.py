"""
Social Preferences Service
Privacy settings, visibility, friend defaults
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from enum import Enum

router = APIRouter(prefix="/preferences/social", tags=["Preferences - Social"])


class VisibilityLevel(str, Enum):
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"


class SocialPreferences(BaseModel):
    user_id: str
    profile_visibility: VisibilityLevel = VisibilityLevel.FRIENDS
    show_parking_status: bool = True
    show_location_to_friends: bool = True
    allow_friend_requests: bool = True
    allow_group_invites: bool = True
    auto_accept_classmates: bool = False
    show_on_leaderboard: bool = True


preferences_db: dict = {}


@router.get("/", response_model=SocialPreferences)
async def get_social_preferences(user_id: str):
    if user_id not in preferences_db:
        preferences_db[user_id] = SocialPreferences(user_id=user_id)
    return preferences_db[user_id]


@router.put("/")
async def update_social_preferences(user_id: str, prefs: SocialPreferences):
    preferences_db[user_id] = prefs
    return {"message": "Preferences updated", "preferences": prefs}


@router.put("/visibility")
async def update_visibility(user_id: str, level: VisibilityLevel):
    if user_id not in preferences_db:
        preferences_db[user_id] = SocialPreferences(user_id=user_id)
    preferences_db[user_id].profile_visibility = level
    return {"message": f"Visibility set to {level.value}"}


@router.put("/parking-status")
async def toggle_parking_status(user_id: str, show: bool):
    if user_id not in preferences_db:
        preferences_db[user_id] = SocialPreferences(user_id=user_id)
    preferences_db[user_id].show_parking_status = show
    return {"message": f"Parking status visibility: {show}"}
