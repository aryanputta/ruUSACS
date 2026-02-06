"""
Classes Service - Student Module
Group students by class schedule for coordinated parking
Azure Service: NONE
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, time
from enum import Enum
import uuid

router = APIRouter(prefix="/student/classes", tags=["Student - Classes"])


class DayOfWeek(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"


class ClassSchedule(BaseModel):
    class_id: str
    course_code: str
    course_name: str
    building: str
    room: Optional[str] = None
    days: List[DayOfWeek]
    start_time: str  # Format: "HH:MM"
    end_time: str
    preferred_lot: Optional[str] = None


class ClassGroup(BaseModel):
    group_id: str
    class_id: str
    course_code: str
    members: List[str]
    member_count: int


class UserSchedule(BaseModel):
    user_id: str
    classes: List[ClassSchedule]
    semester: str


# In-memory store
schedules_db: dict = {}
class_groups_db: dict = {}


@router.get("/schedule", response_model=UserSchedule)
async def get_schedule(user_id: str):
    """Get user's class schedule"""
    if user_id not in schedules_db:
        return UserSchedule(user_id=user_id, classes=[], semester="Spring 2026")
    return schedules_db[user_id]


@router.post("/schedule/add", response_model=ClassSchedule)
async def add_class(user_id: str, class_data: ClassSchedule):
    """Add a class to user's schedule"""
    if user_id not in schedules_db:
        schedules_db[user_id] = UserSchedule(
            user_id=user_id, 
            classes=[], 
            semester="Spring 2026"
        )
    
    new_class = ClassSchedule(
        class_id=str(uuid.uuid4()),
        course_code=class_data.course_code,
        course_name=class_data.course_name,
        building=class_data.building,
        room=class_data.room,
        days=class_data.days,
        start_time=class_data.start_time,
        end_time=class_data.end_time,
        preferred_lot=class_data.preferred_lot
    )
    schedules_db[user_id].classes.append(new_class)
    
    # Auto-join class group
    await _join_class_group(user_id, new_class.course_code)
    
    return new_class


@router.delete("/schedule/{class_id}")
async def remove_class(user_id: str, class_id: str):
    """Remove a class from schedule"""
    if user_id not in schedules_db:
        raise HTTPException(status_code=404, detail="No schedule found")
    
    schedules_db[user_id].classes = [
        c for c in schedules_db[user_id].classes if c.class_id != class_id
    ]
    return {"message": "Class removed"}


@router.get("/classmates/{course_code}", response_model=List[str])
async def get_classmates(user_id: str, course_code: str):
    """Get list of friends in the same class"""
    if course_code not in class_groups_db:
        return []
    return [m for m in class_groups_db[course_code].members if m != user_id]


@router.get("/today", response_model=List[ClassSchedule])
async def get_todays_classes(user_id: str):
    """Get classes for today"""
    if user_id not in schedules_db:
        return []
    
    today = datetime.now().strftime("%A").lower()
    return [c for c in schedules_db[user_id].classes if today in [d.value for d in c.days]]


@router.get("/next")
async def get_next_class(user_id: str):
    """Get the next upcoming class"""
    todays_classes = await get_todays_classes(user_id)
    if not todays_classes:
        return {"message": "No more classes today"}
    
    now = datetime.now().strftime("%H:%M")
    upcoming = [c for c in todays_classes if c.start_time > now]
    
    if upcoming:
        return {"next_class": min(upcoming, key=lambda c: c.start_time)}
    return {"message": "No more classes today"}


async def _join_class_group(user_id: str, course_code: str):
    """Internal: Join or create class group"""
    if course_code not in class_groups_db:
        class_groups_db[course_code] = ClassGroup(
            group_id=str(uuid.uuid4()),
            class_id=course_code,
            course_code=course_code,
            members=[],
            member_count=0
        )
    
    if user_id not in class_groups_db[course_code].members:
        class_groups_db[course_code].members.append(user_id)
        class_groups_db[course_code].member_count += 1
