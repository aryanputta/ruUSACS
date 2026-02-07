"""
CV Integration Service - Parking Detection
Endpoints for the Computer Vision model to report parking spot status
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import httpx

from config.settings import settings
from config.db import get_db_connection

router = APIRouter(prefix="/cv", tags=["CV Integration"])


class SpotDetection(BaseModel):
    lot_name: str
    spot_id: str
    is_occupied: bool
    confidence: float  # 0.0 to 1.0
    timestamp: Optional[str] = None


class BatchDetection(BaseModel):
    detections: List[SpotDetection]
    frame_id: Optional[str] = None
    camera_id: Optional[str] = None


class LotSummary(BaseModel):
    lot_name: str
    total_spots: int
    occupied_spots: int
    available_spots: int
    occupancy_percent: float
    last_updated: str


# In-memory store for spot status
spot_status_db: dict = {}
lot_summaries: dict = {}


@router.post("/detect")
async def report_detection(detection: SpotDetection):
    """Report a single parking spot detection from CV model.
    
    The CV model calls this endpoint whenever it detects a change in spot status.
    """
    key = f"{detection.lot_name}:{detection.spot_id}"
    
    was_occupied = spot_status_db.get(key, {}).get("is_occupied", None)
    
    spot_status_db[key] = {
        "lot_name": detection.lot_name,
        "spot_id": detection.spot_id,
        "is_occupied": detection.is_occupied,
        "confidence": detection.confidence,
        "timestamp": detection.timestamp or datetime.now().isoformat()
    }
    
    # If spot just became available, trigger notification
    if was_occupied == True and detection.is_occupied == False:
        await _notify_spot_available(detection.lot_name, detection.spot_id)
    
    return {"status": "recorded", "key": key}


@router.post("/detect/batch")
async def report_batch_detections(batch: BatchDetection):
    """Report multiple parking spot detections at once.
    
    More efficient for CV models that process entire frames.
    """
    results = []
    spots_freed = []
    
    for detection in batch.detections:
        key = f"{detection.lot_name}:{detection.spot_id}"
        was_occupied = spot_status_db.get(key, {}).get("is_occupied", None)
        
        spot_status_db[key] = {
            "lot_name": detection.lot_name,
            "spot_id": detection.spot_id,
            "is_occupied": detection.is_occupied,
            "confidence": detection.confidence,
            "timestamp": detection.timestamp or datetime.now().isoformat()
        }
        
        if was_occupied == True and detection.is_occupied == False:
            spots_freed.append(detection)
        
        results.append({"key": key, "status": "recorded"})
    
    # Update lot summaries
    await _update_lot_summaries()
    
    # Send notifications for freed spots
    for spot in spots_freed:
        await _notify_spot_available(spot.lot_name, spot.spot_id)
    
    return {
        "status": "batch_recorded",
        "count": len(results),
        "spots_freed": len(spots_freed),
        "frame_id": batch.frame_id
    }


@router.get("/spots/{lot_name}")
async def get_lot_status(lot_name: str):
    """Get current status of all spots in a lot."""
    spots = [v for k, v in spot_status_db.items() if v["lot_name"] == lot_name]
    
    if not spots:
        return {"lot_name": lot_name, "spots": [], "message": "No detections recorded yet"}
    
    occupied = sum(1 for s in spots if s["is_occupied"])
    
    return {
        "lot_name": lot_name,
        "total_spots": len(spots),
        "occupied": occupied,
        "available": len(spots) - occupied,
        "occupancy_percent": round(occupied / len(spots) * 100, 1),
        "spots": spots
    }


@router.get("/summary")
async def get_all_lots_summary():
    """Get summary of all parking lots."""
    await _update_lot_summaries()
    return {"lots": list(lot_summaries.values())}


@router.get("/health")
async def cv_health():
    """Health check for CV integration."""
    return {
        "status": "ready",
        "spots_tracked": len(spot_status_db),
        "lots_tracked": len(lot_summaries)
    }


async def _update_lot_summaries():
    """Update lot summaries from current spot data."""
    lots = {}
    for key, spot in spot_status_db.items():
        lot = spot["lot_name"]
        if lot not in lots:
            lots[lot] = {"total": 0, "occupied": 0}
        lots[lot]["total"] += 1
        if spot["is_occupied"]:
            lots[lot]["occupied"] += 1
    
    for lot, data in lots.items():
        lot_summaries[lot] = LotSummary(
            lot_name=lot,
            total_spots=data["total"],
            occupied_spots=data["occupied"],
            available_spots=data["total"] - data["occupied"],
            occupancy_percent=round(data["occupied"] / data["total"] * 100, 1) if data["total"] > 0 else 0,
            last_updated=datetime.now().isoformat()
        )


async def _notify_spot_available(lot_name: str, spot_id: str):
    """Send push notification when a spot becomes available."""
    if not settings.ntfy_topic:
        return
    
    url = f"https://ntfy.sh/{settings.ntfy_topic}"
    headers = {
        "Title": f"Spot Available: {lot_name}",
        "Priority": "4",
        "Tags": "parking,car"
    }
    message = f"Spot {spot_id} just opened up in {lot_name}"
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, data=message, headers=headers)
    except:
        pass  # Fail silently for notifications
