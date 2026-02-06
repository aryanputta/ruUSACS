"""
Notification Preferences Service
Push notification controls, quiet hours, preferences
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

router = APIRouter(prefix="/preferences/notifications", tags=["Preferences - Notifications"])


class NotificationType(str, Enum):
    FRIEND_REQUEST = "friend_request"
    MESSAGE = "message"
    SPOT_ALERT = "spot_alert"
    CARPOOL = "carpool"
    SAFETY = "safety"
    CHALLENGE = "challenge"
    BADGE = "badge"


class NotificationPreferences(BaseModel):
    user_id: str
    push_enabled: bool = True
    email_enabled: bool = False
    quiet_hours_enabled: bool = False
    quiet_start: str = "22:00"
    quiet_end: str = "08:00"
    enabled_types: List[NotificationType] = list(NotificationType)
    safety_override: bool = True  # Safety notifications bypass quiet hours


preferences_db: dict = {}


@router.get("/", response_model=NotificationPreferences)
async def get_notification_preferences(user_id: str):
    if user_id not in preferences_db:
        preferences_db[user_id] = NotificationPreferences(user_id=user_id)
    return preferences_db[user_id]


@router.put("/")
async def update_notification_preferences(user_id: str, prefs: NotificationPreferences):
    preferences_db[user_id] = prefs
    return {"message": "Notification preferences updated"}


@router.put("/push")
async def toggle_push(user_id: str, enabled: bool):
    if user_id not in preferences_db:
        preferences_db[user_id] = NotificationPreferences(user_id=user_id)
    preferences_db[user_id].push_enabled = enabled
    return {"message": f"Push notifications: {'enabled' if enabled else 'disabled'}"}


@router.put("/quiet-hours")
async def set_quiet_hours(user_id: str, enabled: bool, start: str = "22:00", end: str = "08:00"):
    if user_id not in preferences_db:
        preferences_db[user_id] = NotificationPreferences(user_id=user_id)
    preferences_db[user_id].quiet_hours_enabled = enabled
    preferences_db[user_id].quiet_start = start
    preferences_db[user_id].quiet_end = end
    return {"message": f"Quiet hours: {start} - {end}" if enabled else "Quiet hours disabled"}


@router.put("/type/{notification_type}")
async def toggle_notification_type(user_id: str, notification_type: NotificationType, enabled: bool):
    if user_id not in preferences_db:
        preferences_db[user_id] = NotificationPreferences(user_id=user_id)
    
    if enabled and notification_type not in preferences_db[user_id].enabled_types:
        preferences_db[user_id].enabled_types.append(notification_type)
    elif not enabled and notification_type in preferences_db[user_id].enabled_types:
        preferences_db[user_id].enabled_types.remove(notification_type)
    
    return {"message": f"{notification_type.value}: {'enabled' if enabled else 'disabled'}"}
