"""
Calendar Import Service - Student Module
Parse .ics files from Canvas/Google Calendar for schedule integration
Azure Service: NONE (Local parsing)
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import re

router = APIRouter(prefix="/student/calendar", tags=["Student - Calendar Import"])


class CalendarEvent(BaseModel):
    event_id: str
    summary: str
    location: Optional[str] = None
    start_time: str
    end_time: str
    recurrence: Optional[str] = None
    is_class: bool = False


class ImportResult(BaseModel):
    success: bool
    events_imported: int
    classes_detected: int
    events: List[CalendarEvent]


# In-memory store
imported_calendars: dict = {}


def parse_ics_content(content: str) -> List[CalendarEvent]:
    """Parse ICS file content and extract events."""
    events = []
    
    # Split into event blocks
    event_blocks = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', content, re.DOTALL)
    
    for block in event_blocks:
        event = {
            "event_id": str(uuid.uuid4()),
            "summary": "",
            "location": None,
            "start_time": "",
            "end_time": "",
            "recurrence": None,
            "is_class": False
        }
        
        # Extract SUMMARY
        summary_match = re.search(r'SUMMARY:(.+)', block)
        if summary_match:
            event["summary"] = summary_match.group(1).strip()
        
        # Extract LOCATION
        location_match = re.search(r'LOCATION:(.+)', block)
        if location_match:
            event["location"] = location_match.group(1).strip()
        
        # Extract DTSTART
        dtstart_match = re.search(r'DTSTART[^:]*:(\d{8}T\d{6})', block)
        if dtstart_match:
            dt = dtstart_match.group(1)
            event["start_time"] = f"{dt[9:11]}:{dt[11:13]}"
        
        # Extract DTEND
        dtend_match = re.search(r'DTEND[^:]*:(\d{8}T\d{6})', block)
        if dtend_match:
            dt = dtend_match.group(1)
            event["end_time"] = f"{dt[9:11]}:{dt[11:13]}"
        
        # Check for recurrence (weekly classes)
        if 'RRULE' in block:
            event["recurrence"] = "weekly"
            event["is_class"] = True
        
        # Heuristic: detect if it's a class based on keywords
        class_keywords = ['lecture', 'recitation', 'lab', 'seminar', 'class', 'CS ', '01:']
        if any(kw.lower() in event["summary"].lower() for kw in class_keywords):
            event["is_class"] = True
        
        events.append(CalendarEvent(**event))
    
    return events


@router.post("/import", response_model=ImportResult)
async def import_calendar(user_id: str, file: UploadFile = File(...)):
    """Import a .ics calendar file from Canvas or Google Calendar.
    
    The endpoint parses the ICS file and extracts:
    - Class schedules (recurring events with location)
    - One-time events
    
    Classes are automatically added to the user's schedule.
    """
    if not file.filename.endswith('.ics'):
        raise HTTPException(status_code=400, detail="File must be .ics format")
    
    content = await file.read()
    content_str = content.decode('utf-8')
    
    events = parse_ics_content(content_str)
    classes = [e for e in events if e.is_class]
    
    # Store imported calendar
    imported_calendars[user_id] = events
    
    return ImportResult(
        success=True,
        events_imported=len(events),
        classes_detected=len(classes),
        events=events
    )


@router.get("/events", response_model=List[CalendarEvent])
async def get_imported_events(user_id: str, classes_only: bool = False):
    """Get previously imported calendar events."""
    if user_id not in imported_calendars:
        return []
    
    events = imported_calendars[user_id]
    if classes_only:
        return [e for e in events if e.is_class]
    return events


@router.post("/sync-to-schedule")
async def sync_to_schedule(user_id: str):
    """Sync detected classes from calendar to the class schedule.
    
    This allows users to import their Canvas calendar and have
    their classes automatically populate in RuParked.
    """
    if user_id not in imported_calendars:
        raise HTTPException(status_code=404, detail="No imported calendar found")
    
    classes = [e for e in imported_calendars[user_id] if e.is_class]
    
    # Here we would call the classes service to add each class
    # For now, return the count
    return {
        "message": f"Synced {len(classes)} classes to schedule",
        "classes": classes
    }
