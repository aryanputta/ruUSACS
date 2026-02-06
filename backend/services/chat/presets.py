"""
Presets Service - Chat Module
Quick message templates for common parking scenarios
Azure Service: NONE
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
import uuid

router = APIRouter(prefix="/chat/presets", tags=["Chat - Presets"])


class PresetCategory(str, Enum):
    LEAVING = "leaving"
    SPOT_OPEN = "spot_open"
    RUNNING_LATE = "running_late"
    NEED_SPOT = "need_spot"
    CARPOOL = "carpool"
    SAFETY = "safety"
    CUSTOM = "custom"


class MessagePreset(BaseModel):
    preset_id: str
    user_id: Optional[str] = None  # None for system presets
    category: PresetCategory
    title: str
    content: str
    emoji: Optional[str] = None
    is_system: bool = False


# System presets (available to everyone)
SYSTEM_PRESETS = [
    MessagePreset(preset_id="sys_1", category=PresetCategory.LEAVING, 
                  title="Leaving Now", content="🚗 Leaving now! My spot will be open in ~5 min", 
                  emoji="🚗", is_system=True),
    MessagePreset(preset_id="sys_2", category=PresetCategory.LEAVING,
                  title="Left Campus", content="Just left campus, spot is open!", 
                  emoji="👋", is_system=True),
    MessagePreset(preset_id="sys_3", category=PresetCategory.SPOT_OPEN,
                  title="Spot Available", content="🅿️ Found an open spot if anyone needs it!", 
                  emoji="🅿️", is_system=True),
    MessagePreset(preset_id="sys_4", category=PresetCategory.RUNNING_LATE,
                  title="Running Late", content="⏰ Running late, be there in 10", 
                  emoji="⏰", is_system=True),
    MessagePreset(preset_id="sys_5", category=PresetCategory.NEED_SPOT,
                  title="Need Spot", content="🆘 Anyone leaving soon? Need a spot!", 
                  emoji="🆘", is_system=True),
    MessagePreset(preset_id="sys_6", category=PresetCategory.CARPOOL,
                  title="Room in Car", content="🚙 Have room for 2 more if anyone needs a ride!", 
                  emoji="🚙", is_system=True),
    MessagePreset(preset_id="sys_7", category=PresetCategory.SAFETY,
                  title="Walking to Car", content="🚶 Walking to my car now, heading to Lot X", 
                  emoji="🚶", is_system=True),
]

# User custom presets
user_presets_db: dict = {}


@router.get("/system", response_model=List[MessagePreset])
async def get_system_presets():
    """Get all system presets"""
    return SYSTEM_PRESETS


@router.get("/", response_model=List[MessagePreset])
async def get_all_presets(user_id: str):
    """Get all presets (system + user custom)"""
    user_custom = user_presets_db.get(user_id, [])
    return SYSTEM_PRESETS + user_custom


@router.get("/category/{category}", response_model=List[MessagePreset])
async def get_presets_by_category(user_id: str, category: PresetCategory):
    """Get presets filtered by category"""
    all_presets = SYSTEM_PRESETS + user_presets_db.get(user_id, [])
    return [p for p in all_presets if p.category == category]


@router.post("/custom", response_model=MessagePreset)
async def create_custom_preset(user_id: str, preset: MessagePreset):
    """Create a custom user preset"""
    new_preset = MessagePreset(
        preset_id=str(uuid.uuid4()),
        user_id=user_id,
        category=preset.category,
        title=preset.title,
        content=preset.content,
        emoji=preset.emoji,
        is_system=False
    )
    
    if user_id not in user_presets_db:
        user_presets_db[user_id] = []
    user_presets_db[user_id].append(new_preset)
    
    return new_preset


@router.delete("/custom/{preset_id}")
async def delete_custom_preset(user_id: str, preset_id: str):
    """Delete a custom user preset"""
    if user_id not in user_presets_db:
        raise HTTPException(status_code=404, detail="No custom presets found")
    
    user_presets_db[user_id] = [p for p in user_presets_db[user_id] if p.preset_id != preset_id]
    return {"message": "Preset deleted"}
