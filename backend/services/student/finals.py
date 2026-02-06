"""
Finals Service - Student Module
Special finals-week mode with extended location sharing and stress-relief features
Azure Service: Azure Application Insights
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from enum import Enum

router = APIRouter(prefix="/student/finals", tags=["Student - Finals"])


class FinalsMode(str, Enum):
    OFF = "off"
    STUDY_MODE = "study_mode"
    EXAM_DAY = "exam_day"
    CRAMMING = "cramming"


class FinalExam(BaseModel):
    exam_id: str
    course_code: str
    course_name: str
    exam_date: date
    exam_time: str
    building: str
    room: Optional[str] = None
    study_group_id: Optional[str] = None


class FinalsSettings(BaseModel):
    user_id: str
    mode: FinalsMode = FinalsMode.OFF
    extended_location_sharing: bool = False
    quiet_notifications: bool = True
    study_buddy_enabled: bool = True
    exams: List[FinalExam] = []


# In-memory store
finals_db: dict = {}


@router.get("/settings", response_model=FinalsSettings)
async def get_finals_settings(user_id: str):
    """Get user's finals week settings"""
    if user_id not in finals_db:
        finals_db[user_id] = FinalsSettings(user_id=user_id)
    return finals_db[user_id]


@router.put("/mode")
async def set_finals_mode(user_id: str, mode: FinalsMode):
    """Set finals week mode"""
    if user_id not in finals_db:
        finals_db[user_id] = FinalsSettings(user_id=user_id)
    
    finals_db[user_id].mode = mode
    
    # Auto-enable features based on mode
    if mode in [FinalsMode.STUDY_MODE, FinalsMode.CRAMMING]:
        finals_db[user_id].quiet_notifications = True
    if mode == FinalsMode.EXAM_DAY:
        finals_db[user_id].extended_location_sharing = True
    
    # TODO: Log to Azure Application Insights for finals week analytics
    
    return {"message": f"Finals mode set to {mode.value}", "settings": finals_db[user_id]}


@router.post("/exams", response_model=FinalExam)
async def add_final_exam(user_id: str, exam: FinalExam):
    """Add a final exam to schedule"""
    if user_id not in finals_db:
        finals_db[user_id] = FinalsSettings(user_id=user_id)
    
    finals_db[user_id].exams.append(exam)
    return exam


@router.get("/exams", response_model=List[FinalExam])
async def get_finals_schedule(user_id: str):
    """Get all scheduled final exams"""
    if user_id not in finals_db:
        return []
    return finals_db[user_id].exams


@router.get("/next-exam")
async def get_next_exam(user_id: str):
    """Get the next upcoming final exam"""
    if user_id not in finals_db or not finals_db[user_id].exams:
        return {"message": "No finals scheduled"}
    
    today = date.today()
    upcoming = [e for e in finals_db[user_id].exams if e.exam_date >= today]
    
    if upcoming:
        next_exam = min(upcoming, key=lambda e: e.exam_date)
        days_until = (next_exam.exam_date - today).days
        return {
            "next_exam": next_exam,
            "days_until": days_until,
            "message": f"{days_until} days until {next_exam.course_code} final"
        }
    return {"message": "All finals completed! 🎉"}


@router.get("/study-buddies/{course_code}")
async def find_study_buddies(user_id: str, course_code: str):
    """Find others studying for the same exam"""
    study_buddies = []
    for uid, settings in finals_db.items():
        if uid != user_id and settings.study_buddy_enabled:
            for exam in settings.exams:
                if exam.course_code == course_code:
                    study_buddies.append(uid)
                    break
    return {"course_code": course_code, "study_buddies": study_buddies}


@router.put("/extended-sharing")
async def toggle_extended_sharing(user_id: str, enabled: bool):
    """Toggle extended location sharing for finals week safety"""
    if user_id not in finals_db:
        finals_db[user_id] = FinalsSettings(user_id=user_id)
    
    finals_db[user_id].extended_location_sharing = enabled
    return {"message": f"Extended location sharing {'enabled' if enabled else 'disabled'}"}
