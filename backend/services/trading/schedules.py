"""
Schedule Sharing Service
Students can share class schedules to find parking buddies
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, time
from enum import Enum

router = APIRouter(prefix="/trading/schedules", tags=["Trading - Schedules"])


class DayOfWeek(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class ClassBlock(BaseModel):
    class_name: str
    building: str
    room: Optional[str] = None
    day: DayOfWeek
    start_time: str
    end_time: str


class UserSchedule(BaseModel):
    user_id: str
    semester: str
    classes: List[ClassBlock] = []
    preferred_lots: List[str] = []
    is_public: bool = True
    updated_at: datetime = None


class ScheduleMatch(BaseModel):
    user_id: str
    match_score: int
    overlapping_times: List[dict]
    shared_buildings: List[str]


# In-memory storage
schedules_db: dict = {}


@router.post("/")
async def save_schedule(schedule: UserSchedule):
    """Save or update a user's class schedule"""
    schedule.updated_at = datetime.now()
    schedules_db[schedule.user_id] = schedule.model_dump()
    return {"message": "Schedule saved", "schedule": schedules_db[schedule.user_id]}


@router.get("/{user_id}")
async def get_schedule(user_id: str):
    """Get a user's schedule"""
    if user_id not in schedules_db:
        return {"user_id": user_id, "classes": [], "message": "No schedule found"}
    return schedules_db[user_id]


@router.get("/{user_id}/matches")
async def find_schedule_matches(user_id: str, day: Optional[DayOfWeek] = None):
    """Find students with overlapping schedules for potential parking coordination"""
    if user_id not in schedules_db:
        raise HTTPException(status_code=404, detail="Your schedule not found")
    
    my_schedule = schedules_db[user_id]
    my_classes = my_schedule["classes"]
    matches = []
    
    for other_id, other_schedule in schedules_db.items():
        if other_id == user_id:
            continue
        if not other_schedule.get("is_public", True):
            continue
        
        other_classes = other_schedule["classes"]
        overlaps = []
        shared_buildings = set()
        
        for my_class in my_classes:
            for other_class in other_classes:
                # Check if same day
                if my_class["day"] == other_class["day"]:
                    if day and my_class["day"] != day:
                        continue
                    
                    # Check time overlap (simplified)
                    if my_class["start_time"] == other_class["start_time"]:
                        overlaps.append({
                            "day": my_class["day"],
                            "time": my_class["start_time"],
                            "your_class": my_class["class_name"],
                            "their_class": other_class["class_name"]
                        })
                    
                    # Check same building
                    if my_class["building"] == other_class["building"]:
                        shared_buildings.add(my_class["building"])
        
        if overlaps or shared_buildings:
            matches.append({
                "user_id": other_id,
                "match_score": len(overlaps) * 10 + len(shared_buildings) * 5,
                "overlapping_times": overlaps,
                "shared_buildings": list(shared_buildings)
            })
    
    # Sort by match score
    matches.sort(key=lambda x: x["match_score"], reverse=True)
    
    return {"matches": matches, "count": len(matches)}


@router.post("/{user_id}/add-class")
async def add_class_to_schedule(user_id: str, class_block: ClassBlock):
    """Add a single class to user's schedule"""
    if user_id not in schedules_db:
        schedules_db[user_id] = {
            "user_id": user_id,
            "semester": "Spring 2026",
            "classes": [],
            "preferred_lots": [],
            "is_public": True,
            "updated_at": datetime.now().isoformat()
        }
    
    schedules_db[user_id]["classes"].append(class_block.model_dump())
    schedules_db[user_id]["updated_at"] = datetime.now().isoformat()
    
    return {"message": "Class added", "schedule": schedules_db[user_id]}


@router.delete("/{user_id}/class/{class_name}")
async def remove_class(user_id: str, class_name: str):
    """Remove a class from schedule"""
    if user_id not in schedules_db:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    classes = schedules_db[user_id]["classes"]
    schedules_db[user_id]["classes"] = [c for c in classes if c["class_name"] != class_name]
    
    return {"message": f"Class '{class_name}' removed"}


@router.put("/{user_id}/privacy")
async def toggle_schedule_privacy(user_id: str, is_public: bool):
    """Toggle whether schedule is visible to others"""
    if user_id not in schedules_db:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    schedules_db[user_id]["is_public"] = is_public
    return {"message": f"Schedule visibility set to {'public' if is_public else 'private'}"}


# ============================================================
# FRIEND SCHEDULE COMPARISON FEATURES
# ============================================================

@router.get("/{user_id}/compare/{friend_id}")
async def compare_with_friend(user_id: str, friend_id: str):
    """Compare your schedule with a specific friend's schedule"""
    if user_id not in schedules_db:
        raise HTTPException(status_code=404, detail="Your schedule not found")
    if friend_id not in schedules_db:
        raise HTTPException(status_code=404, detail="Friend's schedule not found")
    
    my_schedule = schedules_db[user_id]
    friend_schedule = schedules_db[friend_id]
    
    my_classes = my_schedule["classes"]
    friend_classes = friend_schedule["classes"]
    
    # Find overlapping times and gaps
    overlapping_times = []
    same_building_times = []
    free_time_overlap = []
    
    for my_class in my_classes:
        for friend_class in friend_classes:
            if my_class["day"] == friend_class["day"]:
                # Same time slot
                if my_class["start_time"] == friend_class["start_time"]:
                    overlapping_times.append({
                        "day": my_class["day"],
                        "time": my_class["start_time"],
                        "your_class": my_class["class_name"],
                        "your_building": my_class["building"],
                        "friend_class": friend_class["class_name"],
                        "friend_building": friend_class["building"]
                    })
                
                # Same building
                if my_class["building"] == friend_class["building"]:
                    same_building_times.append({
                        "day": my_class["day"],
                        "building": my_class["building"],
                        "your_time": f"{my_class['start_time']} - {my_class['end_time']}",
                        "friend_time": f"{friend_class['start_time']} - {friend_class['end_time']}"
                    })
    
    # Calculate compatibility score
    score = len(overlapping_times) * 20 + len(same_building_times) * 10
    
    return {
        "comparison": {
            "your_user_id": user_id,
            "friend_user_id": friend_id,
            "compatibility_score": score,
            "overlapping_class_times": overlapping_times,
            "same_building_times": same_building_times,
            "your_preferred_lots": my_schedule.get("preferred_lots", []),
            "friend_preferred_lots": friend_schedule.get("preferred_lots", [])
        },
        "recommendation": "Great parking buddy!" if score >= 30 else "Some overlap - could coordinate" if score > 0 else "Different schedules"
    }


@router.post("/{user_id}/share-with-friend/{friend_id}")
async def share_schedule_with_friend(user_id: str, friend_id: str):
    """Share your schedule specifically with a friend"""
    if user_id not in schedules_db:
        raise HTTPException(status_code=404, detail="Your schedule not found")
    
    # Add friend to shared list
    if "shared_with" not in schedules_db[user_id]:
        schedules_db[user_id]["shared_with"] = []
    
    if friend_id not in schedules_db[user_id]["shared_with"]:
        schedules_db[user_id]["shared_with"].append(friend_id)
    
    return {"message": f"Schedule shared with {friend_id}"}


@router.get("/{user_id}/friends-schedules")
async def get_friends_schedules(user_id: str, friend_ids: str):
    """Get schedules of multiple friends (comma-separated IDs)"""
    friend_list = [f.strip() for f in friend_ids.split(",")]
    
    friends_data = []
    for friend_id in friend_list:
        if friend_id in schedules_db:
            schedule = schedules_db[friend_id]
            # Only show if public or shared with user
            if schedule.get("is_public", True) or user_id in schedule.get("shared_with", []):
                friends_data.append({
                    "friend_id": friend_id,
                    "classes": schedule["classes"],
                    "preferred_lots": schedule.get("preferred_lots", [])
                })
    
    return {"friends_schedules": friends_data, "count": len(friends_data)}


@router.post("/{user_id}/preferred-lots")
async def set_preferred_lots(user_id: str, lots: List[str]):
    """Set your preferred parking lots"""
    if user_id not in schedules_db:
        schedules_db[user_id] = {
            "user_id": user_id,
            "semester": "Spring 2026",
            "classes": [],
            "preferred_lots": [],
            "is_public": True,
            "updated_at": datetime.now().isoformat()
        }
    
    schedules_db[user_id]["preferred_lots"] = lots
    return {"message": "Preferred lots updated", "lots": lots}


@router.get("/{user_id}/parking-buddies")
async def find_parking_buddies(user_id: str):
    """Find friends with similar schedules who could be parking buddies"""
    if user_id not in schedules_db:
        raise HTTPException(status_code=404, detail="Your schedule not found")
    
    my_schedule = schedules_db[user_id]
    my_lots = set(my_schedule.get("preferred_lots", []))
    
    buddies = []
    for other_id, other_schedule in schedules_db.items():
        if other_id == user_id:
            continue
        if not other_schedule.get("is_public", True):
            continue
        
        other_lots = set(other_schedule.get("preferred_lots", []))
        shared_lots = my_lots & other_lots
        
        # Count schedule overlaps
        overlap_count = 0
        for my_class in my_schedule["classes"]:
            for other_class in other_schedule["classes"]:
                if my_class["day"] == other_class["day"]:
                    if my_class["start_time"] == other_class["start_time"]:
                        overlap_count += 1
        
        if shared_lots or overlap_count > 0:
            buddies.append({
                "user_id": other_id,
                "shared_parking_lots": list(shared_lots),
                "schedule_overlaps": overlap_count,
                "buddy_score": len(shared_lots) * 15 + overlap_count * 10
            })
    
    # Sort by buddy score
    buddies.sort(key=lambda x: x["buddy_score"], reverse=True)
    
    return {"parking_buddies": buddies[:10], "total_matches": len(buddies)}

