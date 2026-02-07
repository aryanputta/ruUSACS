"""
Challenges Service - Sustainability Module
Weekly eco challenges (carpool X times, share spots)
Azure Service: NONE
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date, timedelta
from enum import Enum
import uuid

router = APIRouter(prefix="/sustainability/challenges", tags=["Sustainability - Challenges"])


class ChallengeType(str, Enum):
    CARPOOL = "carpool"
    SPOT_SHARE = "spot_share"
    WALK = "walk"
    BUS = "bus"
    STREAK = "streak"


class ChallengeStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"


class Challenge(BaseModel):
    challenge_id: str
    title: str
    description: str
    challenge_type: ChallengeType
    target: int
    reward_points: int
    start_date: date
    end_date: date
    is_weekly: bool = True


class UserChallenge(BaseModel):
    user_challenge_id: str
    user_id: str
    challenge: Challenge
    progress: int = 0
    status: ChallengeStatus = ChallengeStatus.ACTIVE
    completed_at: Optional[datetime] = None


# Weekly challenges (system-defined)
WEEKLY_CHALLENGES = [
    Challenge(
        challenge_id="weekly_1",
        title="Carpool Champion",
        description="Share 3 carpool rides this week",
        challenge_type=ChallengeType.CARPOOL,
        target=3,
        reward_points=100,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=7),
        is_weekly=True
    ),
    Challenge(
        challenge_id="weekly_2",
        title="Spot Sharer",
        description="Share your parking spot 5 times",
        challenge_type=ChallengeType.SPOT_SHARE,
        target=5,
        reward_points=75,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=7),
        is_weekly=True
    ),
    Challenge(
        challenge_id="weekly_3",
        title="Walk It Out",
        description="Walk to campus 2 times this week",
        challenge_type=ChallengeType.WALK,
        target=2,
        reward_points=50,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=7),
        is_weekly=True
    ),
]

# In-memory store
user_challenges_db: dict = {}
user_points_db: dict = {}


@router.get("/available", response_model=List[Challenge])
async def get_available_challenges():
    """Get all available challenges"""
    return WEEKLY_CHALLENGES


@router.get("/my-challenges", response_model=List[UserChallenge])
async def get_my_challenges(user_id: str):
    """Get user's active challenges"""
    return user_challenges_db.get(user_id, [])


@router.post("/join/{challenge_id}", response_model=UserChallenge)
async def join_challenge(user_id: str, challenge_id: str):
    """Join a challenge"""
    challenge = next((c for c in WEEKLY_CHALLENGES if c.challenge_id == challenge_id), None)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    if user_id not in user_challenges_db:
        user_challenges_db[user_id] = []
    
    # Check if already joined
    for uc in user_challenges_db[user_id]:
        if uc.challenge.challenge_id == challenge_id:
            raise HTTPException(status_code=400, detail="Already joined")
    
    user_challenge = UserChallenge(
        user_challenge_id=str(uuid.uuid4()),
        user_id=user_id,
        challenge=challenge
    )
    
    user_challenges_db[user_id].append(user_challenge)
    return user_challenge


@router.post("/progress/{challenge_id}")
async def update_progress(user_id: str, challenge_id: str, increment: int = 1):
    """Update challenge progress"""
    if user_id not in user_challenges_db:
        raise HTTPException(status_code=404, detail="No challenges found")
    
    for uc in user_challenges_db[user_id]:
        if uc.challenge.challenge_id == challenge_id:
            if uc.status != ChallengeStatus.ACTIVE:
                raise HTTPException(status_code=400, detail="Challenge not active")
            
            uc.progress += increment
            
            if uc.progress >= uc.challenge.target:
                uc.status = ChallengeStatus.COMPLETED
                uc.completed_at = datetime.utcnow()
                
                # Award points
                if user_id not in user_points_db:
                    user_points_db[user_id] = 0
                user_points_db[user_id] += uc.challenge.reward_points
                
                return {
                    "message": "Challenge completed! 🎉",
                    "points_earned": uc.challenge.reward_points,
                    "total_points": user_points_db[user_id]
                }
            
            return {"message": "Progress updated", "progress": uc.progress, "target": uc.challenge.target}
    
    raise HTTPException(status_code=404, detail="Challenge not found")


@router.get("/points")
async def get_points(user_id: str):
    """Get user's reward points"""
    return {"user_id": user_id, "points": user_points_db.get(user_id, 0)}
