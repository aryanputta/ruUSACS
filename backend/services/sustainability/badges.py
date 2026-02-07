"""
Badges Service - Sustainability Module
Earn sustainability badges for eco-friendly behavior
Azure Service: NONE
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

router = APIRouter(prefix="/sustainability/badges", tags=["Sustainability - Badges"])


class BadgeTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class BadgeCategory(str, Enum):
    CARPOOL = "carpool"
    SPOT_SHARING = "spot_sharing"
    CO2_SAVINGS = "co2_savings"
    STREAKS = "streaks"
    COMMUNITY = "community"


class Badge(BaseModel):
    badge_id: str
    name: str
    description: str
    category: BadgeCategory
    tier: BadgeTier
    icon: str  # Emoji or icon name
    requirement: str
    points_required: Optional[int] = None


class UserBadge(BaseModel):
    user_id: str
    badge: Badge
    earned_at: datetime


# System badges
ALL_BADGES = [
    # Carpool badges
    Badge(badge_id="carpool_bronze", name="Carpool Starter", 
          description="Complete your first carpool", category=BadgeCategory.CARPOOL,
          tier=BadgeTier.BRONZE, icon="🚗", requirement="1 carpool trip"),
    Badge(badge_id="carpool_silver", name="Carpool Regular", 
          description="Complete 10 carpool trips", category=BadgeCategory.CARPOOL,
          tier=BadgeTier.SILVER, icon="🚙", requirement="10 carpool trips"),
    Badge(badge_id="carpool_gold", name="Carpool Champion", 
          description="Complete 50 carpool trips", category=BadgeCategory.CARPOOL,
          tier=BadgeTier.GOLD, icon="🏆", requirement="50 carpool trips"),
    
    # Spot sharing badges
    Badge(badge_id="spots_bronze", name="Spot Sharer", 
          description="Share your first parking spot", category=BadgeCategory.SPOT_SHARING,
          tier=BadgeTier.BRONZE, icon="🅿️", requirement="1 spot shared"),
    Badge(badge_id="spots_silver", name="Generous Parker", 
          description="Share 25 parking spots", category=BadgeCategory.SPOT_SHARING,
          tier=BadgeTier.SILVER, icon="🎁", requirement="25 spots shared"),
    Badge(badge_id="spots_gold", name="Parking Hero", 
          description="Share 100 parking spots", category=BadgeCategory.SPOT_SHARING,
          tier=BadgeTier.GOLD, icon="🦸", requirement="100 spots shared"),
    
    # CO2 badges
    Badge(badge_id="co2_bronze", name="Eco Starter", 
          description="Save 10kg of CO2", category=BadgeCategory.CO2_SAVINGS,
          tier=BadgeTier.BRONZE, icon="🌱", requirement="10kg CO2 saved"),
    Badge(badge_id="co2_silver", name="Planet Protector", 
          description="Save 50kg of CO2", category=BadgeCategory.CO2_SAVINGS,
          tier=BadgeTier.SILVER, icon="🌍", requirement="50kg CO2 saved"),
    Badge(badge_id="co2_gold", name="Earth Guardian", 
          description="Save 200kg of CO2", category=BadgeCategory.CO2_SAVINGS,
          tier=BadgeTier.GOLD, icon="🌳", requirement="200kg CO2 saved"),
    
    # Streak badges
    Badge(badge_id="streak_7", name="Week Warrior", 
          description="7-day sustainability streak", category=BadgeCategory.STREAKS,
          tier=BadgeTier.BRONZE, icon="🔥", requirement="7-day streak"),
    Badge(badge_id="streak_30", name="Month Master", 
          description="30-day sustainability streak", category=BadgeCategory.STREAKS,
          tier=BadgeTier.SILVER, icon="💪", requirement="30-day streak"),
    
    # Community badges
    Badge(badge_id="community_helper", name="Community Helper", 
          description="Help 10 people find parking", category=BadgeCategory.COMMUNITY,
          tier=BadgeTier.SILVER, icon="🤝", requirement="Help 10 people"),
]

# In-memory store
user_badges_db: dict = {}


@router.get("/all", response_model=List[Badge])
async def get_all_badges():
    """Get all available badges"""
    return ALL_BADGES


@router.get("/", response_model=List[UserBadge])
async def get_user_badges(user_id: str):
    """Get user's earned badges"""
    return user_badges_db.get(user_id, [])


@router.get("/progress")
async def get_badge_progress(user_id: str):
    """Get progress toward unearned badges"""
    earned = [ub.badge.badge_id for ub in user_badges_db.get(user_id, [])]
    unearned = [b for b in ALL_BADGES if b.badge_id not in earned]
    
    # TODO: Calculate actual progress based on user metrics
    return {
        "earned_count": len(earned),
        "total_badges": len(ALL_BADGES),
        "next_badges": unearned[:3]  # Show next 3 achievable badges
    }


@router.post("/award/{badge_id}")
async def award_badge(user_id: str, badge_id: str):
    """Award a badge to user (internal use)"""
    badge = next((b for b in ALL_BADGES if b.badge_id == badge_id), None)
    if not badge:
        return {"error": "Badge not found"}
    
    if user_id not in user_badges_db:
        user_badges_db[user_id] = []
    
    # Check if already earned
    for ub in user_badges_db[user_id]:
        if ub.badge.badge_id == badge_id:
            return {"message": "Badge already earned"}
    
    user_badge = UserBadge(
        user_id=user_id,
        badge=badge,
        earned_at=datetime.utcnow()
    )
    
    user_badges_db[user_id].append(user_badge)
    
    return {"message": f"Badge earned: {badge.name}! {badge.icon}", "badge": badge}


@router.get("/showcase")
async def get_badge_showcase(user_id: str):
    """Get user's badge showcase for profile"""
    badges = user_badges_db.get(user_id, [])
    
    return {
        "total_badges": len(badges),
        "badges_by_tier": {
            "platinum": len([b for b in badges if b.badge.tier == BadgeTier.PLATINUM]),
            "gold": len([b for b in badges if b.badge.tier == BadgeTier.GOLD]),
            "silver": len([b for b in badges if b.badge.tier == BadgeTier.SILVER]),
            "bronze": len([b for b in badges if b.badge.tier == BadgeTier.BRONZE]),
        },
        "featured_badges": badges[:5] if badges else []
    }
