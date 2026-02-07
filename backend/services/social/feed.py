"""
Social Feed Service - Parking Lot News & Alerts.
Provides a platform for users to share real-time updates, alerts, and feedback 
about specific parking lots. Supports liking and replying to posts.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/social/feed", tags=["Social - Feed"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class PostType(str, Enum):
    NEWS = "news"
    ALERT = "alert"
    EVENT = "event"


class Reply(BaseModel):
    reply_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Post(BaseModel):
    post_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    lot_id: str
    type: PostType = PostType.NEWS
    content: str
    likes: List[str] = Field(default_factory=list, description="List of user IDs who liked the post")
    replies: List[Reply] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PostCreate(BaseModel):
    user_id: str
    lot_id: str
    content: str
    type: PostType = PostType.NEWS


class ReplyCreate(BaseModel):
    user_id: str
    content: str


# ---------------------------------------------------------------------------
# In-Memory Storage
# ---------------------------------------------------------------------------

# In a real app, this would be a database (PostgreSQL/CosmosDB)
posts_db: Dict[str, Post] = {}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/post", response_model=Post)
async def create_post(payload: PostCreate):
    """Create a new post or alert for a specific parking lot."""
    new_post = Post(
        user_id=payload.user_id,
        lot_id=payload.lot_id,
        content=payload.content,
        type=payload.type
    )
    posts_db[new_post.post_id] = new_post
    return new_post


@router.get("/lot/{lot_id}", response_model=List[Post])
async def get_lot_feed(lot_id: str):
    """Retrieve all posts for a specific parking lot, sorted by most recent."""
    lot_posts = [p for p in posts_db.values() if p.lot_id == lot_id]
    return sorted(lot_posts, key=lambda x: x.created_at, reverse=True)


@router.get("/alerts", response_model=List[Post])
async def get_active_alerts(lot_id: Optional[str] = None):
    """Retrieve all active alerts, optionally filtered by lot."""
    alerts = [p for p in posts_db.values() if p.type == PostType.ALERT]
    if lot_id:
        alerts = [p for p in alerts if p.lot_id == lot_id]
    return sorted(alerts, key=lambda x: x.created_at, reverse=True)


@router.post("/like/{post_id}")
async def toggle_like(post_id: str, user_id: str):
    """Like or unlike a post."""
    if post_id not in posts_db:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post = posts_db[post_id]
    if user_id in post.likes:
        post.likes.remove(user_id)
        return {"message": "Post unliked", "likes_count": len(post.likes)}
    else:
        post.likes.append(user_id)
        return {"message": "Post liked", "likes_count": len(post.likes)}


@router.post("/reply/{post_id}", response_model=Reply)
async def add_reply(post_id: str, payload: ReplyCreate):
    """Add a reply to an existing post."""
    if post_id not in posts_db:
        raise HTTPException(status_code=404, detail="Post not found")
    
    new_reply = Reply(
        user_id=payload.user_id,
        content=payload.content
    )
    posts_db[post_id].replies.append(new_reply)
    return new_reply


@router.get("/all", response_model=List[Post])
async def get_all_posts():
    """Debug helper to view all posts across all lots."""
    return sorted(posts_db.values(), key=lambda x: x.created_at, reverse=True)
