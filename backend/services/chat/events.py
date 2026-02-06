"""
Events Service - Chat Module
Chat notifications, read receipts, typing indicators
Azure Service: Azure Notification Hubs
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum
import uuid

router = APIRouter(prefix="/chat/events", tags=["Chat - Events"])


class EventType(str, Enum):
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_READ = "message_read"
    TYPING_START = "typing_start"
    TYPING_STOP = "typing_stop"
    USER_ONLINE = "user_online"
    USER_OFFLINE = "user_offline"
    SPOT_ALERT = "spot_alert"
    FRIEND_LEAVING = "friend_leaving"


class ChatEvent(BaseModel):
    event_id: str
    event_type: EventType
    sender_id: str
    recipient_id: str
    conversation_id: Optional[str] = None
    data: Optional[dict] = None
    timestamp: datetime


class TypingIndicator(BaseModel):
    user_id: str
    conversation_id: str
    is_typing: bool


# In-memory store for active typing indicators
typing_indicators: dict = {}


@router.post("/typing")
async def send_typing_indicator(user_id: str, conversation_id: str, is_typing: bool):
    """Send typing indicator to conversation"""
    key = f"{conversation_id}:{user_id}"
    
    if is_typing:
        typing_indicators[key] = TypingIndicator(
            user_id=user_id,
            conversation_id=conversation_id,
            is_typing=True
        )
    else:
        typing_indicators.pop(key, None)
    
    # TODO: Broadcast via WebSocket/Azure Communication Services
    return {"message": "Typing indicator sent"}


@router.get("/typing/{conversation_id}")
async def get_typing_users(conversation_id: str) -> List[str]:
    """Get users currently typing in a conversation"""
    typing_users = []
    for key, indicator in typing_indicators.items():
        if indicator.conversation_id == conversation_id and indicator.is_typing:
            typing_users.append(indicator.user_id)
    return typing_users


@router.post("/read-receipt")
async def send_read_receipt(user_id: str, conversation_id: str, message_id: str):
    """Send read receipt for a message"""
    event = ChatEvent(
        event_id=str(uuid.uuid4()),
        event_type=EventType.MESSAGE_READ,
        sender_id=user_id,
        recipient_id="",  # Will be filled based on conversation
        conversation_id=conversation_id,
        data={"message_id": message_id},
        timestamp=datetime.utcnow()
    )
    
    # TODO: Broadcast via Azure Notification Hubs
    return {"message": "Read receipt sent", "event": event}


@router.post("/spot-alert")
async def send_spot_alert(user_id: str, lot_name: str, message: Optional[str] = None):
    """Send spot alert to friends"""
    event = ChatEvent(
        event_id=str(uuid.uuid4()),
        event_type=EventType.SPOT_ALERT,
        sender_id=user_id,
        recipient_id="friends",  # Broadcast to all friends
        data={
            "lot_name": lot_name,
            "message": message or f"Spot opening up in {lot_name}!"
        },
        timestamp=datetime.utcnow()
    )
    
    # TODO: Send push notification via Azure Notification Hubs
    return {"message": "Spot alert sent to friends", "event": event}


@router.post("/leaving-alert")
async def send_leaving_alert(user_id: str, eta_minutes: int = 5):
    """Alert friends that user is leaving (spot will be open)"""
    event = ChatEvent(
        event_id=str(uuid.uuid4()),
        event_type=EventType.FRIEND_LEAVING,
        sender_id=user_id,
        recipient_id="friends",
        data={
            "eta_minutes": eta_minutes,
            "message": f"Leaving in ~{eta_minutes} minutes, spot will be open!"
        },
        timestamp=datetime.utcnow()
    )
    
    # TODO: Send push notification
    return {"message": "Leaving alert sent", "event": event}
