"""
Messages Service - Chat Module
Real-time 1:1 and group messaging between friends
Azure Service: Azure Communication Services
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum
import uuid

router = APIRouter(prefix="/chat/messages", tags=["Chat - Messages"])


class MessageType(str, Enum):
    TEXT = "text"
    PRESET = "preset"
    LOCATION = "location"
    SPOT_ALERT = "spot_alert"


class Message(BaseModel):
    message_id: str
    sender_id: str
    sender_name: str
    recipient_id: Optional[str] = None  # None for group messages
    group_id: Optional[str] = None
    content: str
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime
    read: bool = False


class SendMessageInput(BaseModel):
    recipient_id: Optional[str] = None
    group_id: Optional[str] = None
    content: str
    message_type: MessageType = MessageType.TEXT


class Conversation(BaseModel):
    conversation_id: str
    participants: List[str]
    last_message: Optional[Message] = None
    unread_count: int = 0


# In-memory store
messages_db: List[Message] = []
conversations_db: dict = {}


@router.get("/conversations", response_model=List[Conversation])
async def get_conversations(user_id: str):
    """Get all conversations for a user"""
    user_convos = []
    for convo in conversations_db.values():
        if user_id in convo.participants:
            user_convos.append(convo)
    return sorted(user_convos, key=lambda c: c.last_message.timestamp if c.last_message else datetime.min, reverse=True)


@router.get("/{conversation_id}", response_model=List[Message])
async def get_messages(conversation_id: str, limit: int = 50, offset: int = 0):
    """Get messages in a conversation"""
    convo_messages = [m for m in messages_db if 
                      (m.recipient_id == conversation_id or m.sender_id == conversation_id)]
    return convo_messages[offset:offset + limit]


@router.post("/send", response_model=Message)
async def send_message(user_id: str, message_data: SendMessageInput):
    """Send a message to a friend or group"""
    if not message_data.recipient_id and not message_data.group_id:
        raise HTTPException(status_code=400, detail="Must specify recipient or group")
    
    new_message = Message(
        message_id=str(uuid.uuid4()),
        sender_id=user_id,
        sender_name=f"User {user_id}",
        recipient_id=message_data.recipient_id,
        group_id=message_data.group_id,
        content=message_data.content,
        message_type=message_data.message_type,
        timestamp=datetime.utcnow()
    )
    messages_db.append(new_message)
    
    # TODO: Send via Azure Communication Services for real-time delivery
    # TODO: Send push notification for offline users
    
    return new_message


@router.put("/{message_id}/read")
async def mark_as_read(user_id: str, message_id: str):
    """Mark a message as read"""
    for msg in messages_db:
        if msg.message_id == message_id:
            msg.read = True
            return {"message": "Marked as read"}
    raise HTTPException(status_code=404, detail="Message not found")


@router.delete("/{message_id}")
async def delete_message(user_id: str, message_id: str):
    """Delete a message (sender only)"""
    global messages_db
    for i, msg in enumerate(messages_db):
        if msg.message_id == message_id:
            if msg.sender_id != user_id:
                raise HTTPException(status_code=403, detail="Can only delete own messages")
            messages_db.pop(i)
            return {"message": "Message deleted"}
    raise HTTPException(status_code=404, detail="Message not found")
