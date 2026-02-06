"""
Emergency Service - Safety Module
One-tap emergency share to trusted contacts
Azure Service: Azure Notification Hubs
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

router = APIRouter(prefix="/safety/emergency", tags=["Safety - Emergency"])


class EmergencyContact(BaseModel):
    contact_id: str
    user_id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    is_primary: bool = False


class EmergencyAlert(BaseModel):
    alert_id: str
    user_id: str
    location: dict  # {lat, lng}
    message: Optional[str] = None
    contacts_notified: List[str]
    timestamp: datetime
    resolved: bool = False


class EmergencySettings(BaseModel):
    user_id: str
    contacts: List[EmergencyContact]
    quick_message: str = "I need help! This is my current location."
    include_location: bool = True
    notify_campus_security: bool = False


# In-memory store
settings_db: dict = {}
alerts_db: List[EmergencyAlert] = []


@router.get("/contacts", response_model=List[EmergencyContact])
async def get_emergency_contacts(user_id: str):
    """Get user's emergency contacts"""
    if user_id not in settings_db:
        return []
    return settings_db[user_id].contacts


@router.post("/contacts", response_model=EmergencyContact)
async def add_emergency_contact(user_id: str, name: str, phone: Optional[str] = None, 
                                 email: Optional[str] = None, is_primary: bool = False):
    """Add an emergency contact"""
    if user_id not in settings_db:
        settings_db[user_id] = EmergencySettings(user_id=user_id, contacts=[])
    
    contact = EmergencyContact(
        contact_id=str(uuid.uuid4()),
        user_id=user_id,
        name=name,
        phone=phone,
        email=email,
        is_primary=is_primary
    )
    
    settings_db[user_id].contacts.append(contact)
    return contact


@router.delete("/contacts/{contact_id}")
async def remove_emergency_contact(user_id: str, contact_id: str):
    """Remove an emergency contact"""
    if user_id not in settings_db:
        raise HTTPException(status_code=404, detail="No contacts found")
    
    settings_db[user_id].contacts = [
        c for c in settings_db[user_id].contacts if c.contact_id != contact_id
    ]
    return {"message": "Contact removed"}


@router.post("/trigger", response_model=EmergencyAlert)
async def trigger_emergency(user_id: str, lat: float, lng: float, 
                            message: Optional[str] = None):
    """TRIGGER EMERGENCY ALERT - sends to all emergency contacts"""
    if user_id not in settings_db or not settings_db[user_id].contacts:
        raise HTTPException(status_code=400, 
                          detail="No emergency contacts configured")
    
    settings = settings_db[user_id]
    contact_ids = [c.contact_id for c in settings.contacts]
    
    alert = EmergencyAlert(
        alert_id=str(uuid.uuid4()),
        user_id=user_id,
        location={"lat": lat, "lng": lng},
        message=message or settings.quick_message,
        contacts_notified=contact_ids,
        timestamp=datetime.utcnow()
    )
    
    alerts_db.append(alert)
    
    # TODO: Send push notifications via Azure Notification Hubs
    # TODO: Send SMS via Azure Communication Services
    # TODO: Optionally notify campus security
    
    return alert


@router.post("/resolve/{alert_id}")
async def resolve_emergency(user_id: str, alert_id: str):
    """Mark an emergency as resolved (user is safe)"""
    for alert in alerts_db:
        if alert.alert_id == alert_id and alert.user_id == user_id:
            alert.resolved = True
            
            # TODO: Notify contacts that user is safe
            
            return {"message": "Emergency resolved. Contacts notified you're safe."}
    
    raise HTTPException(status_code=404, detail="Alert not found")


@router.get("/history", response_model=List[EmergencyAlert])
async def get_emergency_history(user_id: str):
    """Get history of emergency alerts"""
    return [a for a in alerts_db if a.user_id == user_id]


@router.put("/settings")
async def update_emergency_settings(user_id: str, quick_message: Optional[str] = None,
                                     include_location: Optional[bool] = None,
                                     notify_campus_security: Optional[bool] = None):
    """Update emergency settings"""
    if user_id not in settings_db:
        settings_db[user_id] = EmergencySettings(user_id=user_id, contacts=[])
    
    if quick_message is not None:
        settings_db[user_id].quick_message = quick_message
    if include_location is not None:
        settings_db[user_id].include_location = include_location
    if notify_campus_security is not None:
        settings_db[user_id].notify_campus_security = notify_campus_security
    
    return {"message": "Settings updated", "settings": settings_db[user_id]}
