"""
Smart Commute Optimization - Fastest Total Commute (Drive + Walk)

Uses the Azure Maps Route Matrix API to evaluate multi-modal commute options.
Given an origin, a destination, and a set of candidate transition points
(e.g. parking lots, transit stops), the service:

  1. Requests a driving route-matrix from the origin to every candidate transition point.
  2. Requests a walking route-matrix from every candidate transition point to the final destination.
  3. Combines the two legs and returns the transition point that yields the shortest
     total travel time, along with full summary data for both legs.

Converted from TypeScript to Python for consistency with FastAPI backend.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import httpx
import asyncio
import os
from config.azure import AZURE_MAPS_SUBSCRIPTION_KEY

router = APIRouter(prefix="/navigation/commute", tags=["Navigation - Commute Optimization"])

AZURE_MAPS_BASE_URL = os.getenv("AZURE_MAPS_BASE_URL", "https://atlas.microsoft.com")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class GeoPoint(BaseModel):
    """A geographic coordinate (latitude / longitude)."""
    latitude: float
    longitude: float
    label: Optional[str] = None


class RouteLegSummary(BaseModel):
    """Summary for a single route leg returned by Azure Maps."""
    travel_time_seconds: int
    length_meters: int
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None


class TransitionCandidate(BaseModel):
    """A candidate transition point with the combined commute analysis."""
    point: GeoPoint
    label: Optional[str] = None
    drive_leg: RouteLegSummary
    walk_leg: RouteLegSummary
    total_travel_time_seconds: int
    total_length_meters: int


class CommuteOptimizationRequest(BaseModel):
    """Input payload for the optimisation request."""
    origin: GeoPoint
    destination: GeoPoint
    transition_points: List[GeoPoint]
    depart_at: Optional[str] = None


class CommuteOptimizationResult(BaseModel):
    """Full response returned by the optimisation service."""
    origin: GeoPoint
    destination: GeoPoint
    best: TransitionCandidate
    candidates: List[TransitionCandidate]


# ---------------------------------------------------------------------------
# Azure Maps Route Matrix helpers
# ---------------------------------------------------------------------------

async def fetch_route_matrix(
    origins: List[GeoPoint],
    destinations: List[GeoPoint],
    travel_mode: str,  # "car" or "pedestrian"
    depart_at: Optional[str] = None
) -> dict:
    """
    Calls the Azure Maps Post Route Matrix Sync endpoint.
    
    Args:
        origins: Array of origin coordinates.
        destinations: Array of destination coordinates.
        travel_mode: "car" or "pedestrian"
        depart_at: Optional ISO-8601 departure time.
    
    Returns:
        The parsed matrix response.
    """
    if not AZURE_MAPS_SUBSCRIPTION_KEY:
        raise HTTPException(status_code=500, detail="Azure Maps key not configured")
    
    url = f"{AZURE_MAPS_BASE_URL}/route/matrix/sync/json"
    params = {
        "api-version": "1.0",
        "subscription-key": AZURE_MAPS_SUBSCRIPTION_KEY,
        "travelMode": travel_mode,
        "routeType": "fastest"
    }
    
    if depart_at:
        params["departAt"] = depart_at
    
    body = {
        "origins": {
            "type": "MultiPoint",
            "coordinates": [[p.longitude, p.latitude] for p in origins]
        },
        "destinations": {
            "type": "MultiPoint",
            "coordinates": [[p.longitude, p.latitude] for p in destinations]
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, params=params, json=body)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Azure Maps API error: {response.text}"
            )
        
        return response.json()


def build_unreachable_candidate(tp: GeoPoint) -> TransitionCandidate:
    """Build a candidate marked as unreachable."""
    unreachable = RouteLegSummary(
        travel_time_seconds=999999999,
        length_meters=999999999
    )
    return TransitionCandidate(
        point=tp,
        label=tp.label,
        drive_leg=unreachable,
        walk_leg=unreachable,
        total_travel_time_seconds=999999999,
        total_length_meters=999999999
    )


# ---------------------------------------------------------------------------
# Core optimisation logic
# ---------------------------------------------------------------------------

async def compute_fastest_commute(request: CommuteOptimizationRequest) -> CommuteOptimizationResult:
    """
    Computes the fastest combined drive + walk commute.
    
    The algorithm fans out two route-matrix requests in parallel:
      • Drive matrix: origin → each transition point
      • Walk matrix: each transition point → destination
    
    It then zips the results per transition point, sums the travel times,
    and selects the candidate with the lowest total.
    """
    origin = request.origin
    destination = request.destination
    transition_points = request.transition_points
    depart_at = request.depart_at
    
    if not transition_points or len(transition_points) == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one transition point is required for drive+walk optimisation."
        )
    
    # Fan out both matrix requests in parallel
    drive_matrix, walk_matrix = await asyncio.gather(
        fetch_route_matrix([origin], transition_points, "car", depart_at),
        fetch_route_matrix(transition_points, [destination], "pedestrian", depart_at)
    )
    
    # The drive matrix has 1 origin row and N destination columns
    drive_row = drive_matrix.get("matrix", [[]])[0]
    # The walk matrix has N origin rows, each with 1 destination column
    walk_rows = walk_matrix.get("matrix", [])
    
    candidates: List[TransitionCandidate] = []
    
    for idx, tp in enumerate(transition_points):
        # Drive leg - origin → transition point (row 0, col idx)
        drive_cell = drive_row[idx] if idx < len(drive_row) else None
        drive_summary = drive_cell.get("response", {}).get("routeSummary") if drive_cell else None
        
        if not drive_summary or drive_cell.get("statusCode") != 200:
            candidates.append(build_unreachable_candidate(tp))
            continue
        
        # Walk leg - transition point → destination (row idx, col 0)
        walk_cell = walk_rows[idx][0] if idx < len(walk_rows) and len(walk_rows[idx]) > 0 else None
        walk_summary = walk_cell.get("response", {}).get("routeSummary") if walk_cell else None
        
        if not walk_summary or walk_cell.get("statusCode") != 200:
            candidates.append(build_unreachable_candidate(tp))
            continue
        
        drive_leg = RouteLegSummary(
            travel_time_seconds=drive_summary.get("travelTimeInSeconds", 0),
            length_meters=drive_summary.get("lengthInMeters", 0),
            departure_time=drive_summary.get("departureTime"),
            arrival_time=drive_summary.get("arrivalTime")
        )
        
        walk_leg = RouteLegSummary(
            travel_time_seconds=walk_summary.get("travelTimeInSeconds", 0),
            length_meters=walk_summary.get("lengthInMeters", 0),
            departure_time=walk_summary.get("departureTime"),
            arrival_time=walk_summary.get("arrivalTime")
        )
        
        candidates.append(TransitionCandidate(
            point=GeoPoint(latitude=tp.latitude, longitude=tp.longitude),
            label=tp.label,
            drive_leg=drive_leg,
            walk_leg=walk_leg,
            total_travel_time_seconds=drive_leg.travel_time_seconds + walk_leg.travel_time_seconds,
            total_length_meters=drive_leg.length_meters + walk_leg.length_meters
        ))
    
    # Sort ascending by total travel time
    candidates.sort(key=lambda c: c.total_travel_time_seconds)
    
    return CommuteOptimizationResult(
        origin=origin,
        destination=destination,
        best=candidates[0],
        candidates=candidates
    )


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@router.post("/optimize")
async def optimize_commute(request: CommuteOptimizationRequest):
    """
    Calculate the fastest combined drive + walk commute.
    
    Request body example:
    {
        "origin": {"latitude": 40.5008, "longitude": -74.4474},
        "destination": {"latitude": 40.5230, "longitude": -74.4580},
        "transition_points": [
            {"latitude": 40.5120, "longitude": -74.4510, "label": "Lot A"},
            {"latitude": 40.5170, "longitude": -74.4530, "label": "Lot B"}
        ],
        "depart_at": "2026-02-06T08:00:00-05:00"
    }
    """
    result = await compute_fastest_commute(request)
    return {"success": True, "data": result}


@router.get("/health")
async def commute_health():
    """Lightweight health-check endpoint for commute service."""
    from datetime import datetime
    return {
        "success": True,
        "service": "smart-commute-optimization",
        "timestamp": datetime.now().isoformat()
    }


# ---------------------------------------------------------------------------
# Simple route finding (without matrix - for single routes)
# ---------------------------------------------------------------------------

@router.get("/route")
async def get_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    travel_mode: str = "car"
):
    """Get a simple route between two points."""
    if not AZURE_MAPS_SUBSCRIPTION_KEY:
        raise HTTPException(status_code=500, detail="Azure Maps key not configured")
    
    url = f"{AZURE_MAPS_BASE_URL}/route/directions/json"
    params = {
        "api-version": "1.0",
        "subscription-key": AZURE_MAPS_SUBSCRIPTION_KEY,
        "query": f"{origin_lat},{origin_lng}:{dest_lat},{dest_lng}",
        "travelMode": travel_mode,
        "routeType": "fastest"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Azure Maps API error: {response.text}"
            )
        
        data = response.json()
        routes = data.get("routes", [])
        
        if not routes:
            return {"success": False, "message": "No route found"}
        
        route = routes[0]
        summary = route.get("summary", {})
        
        return {
            "success": True,
            "route": {
                "travel_time_seconds": summary.get("travelTimeInSeconds", 0),
                "length_meters": summary.get("lengthInMeters", 0),
                "departure_time": summary.get("departureTime"),
                "arrival_time": summary.get("arrivalTime"),
                "traffic_delay_seconds": summary.get("trafficDelayInSeconds", 0)
            }
        }


@router.get("/parking-lots")
async def get_rutgers_parking_lots():
    """Get a list of Rutgers parking lots as transition points."""
    # Common Rutgers parking lots (hardcoded for demo)
    lots = [
        {"latitude": 40.5023, "longitude": -74.4512, "label": "Lot 48 - Livingston"},
        {"latitude": 40.5217, "longitude": -74.4377, "label": "Lot 60 - Busch"},
        {"latitude": 40.4986, "longitude": -74.4479, "label": "Lot 55 - Livingston"},
        {"latitude": 40.5012, "longitude": -74.4642, "label": "Stadium Lot"},
        {"latitude": 40.5267, "longitude": -74.4593, "label": "Lot 67 - Busch"},
        {"latitude": 40.4830, "longitude": -74.4337, "label": "College Ave Deck"},
        {"latitude": 40.4802, "longitude": -74.4265, "label": "Lot 26 - College Ave"},
        {"latitude": 40.5196, "longitude": -74.4630, "label": "Lot 64 - Busch"},
    ]
    return {"lots": lots, "count": len(lots)}
