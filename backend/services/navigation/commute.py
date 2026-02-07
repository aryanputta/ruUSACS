"""
REST routes for the Smart Commute Optimization API.

All functionality is exposed as HTTP endpoints so the frontend never
needs direct access to Azure services or keys.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

# ADAPTED IMPORT: 'backend.config' -> 'config.settings'
from config.settings import settings
from services.navigation.optimization import (
    CommuteOptimizationRequest,
    CommuteOptimizationResult,
    compute_fastest_commute,
)

router = APIRouter(prefix="/navigation/commute", tags=["Navigation - Commute Optimization"])


# ---------------------------------------------------------------------------
# Response wrappers
# ---------------------------------------------------------------------------


class SuccessResponse(BaseModel):
    success: bool = True
    data: CommuteOptimizationResult


class HealthResponse(BaseModel):
    success: bool = True
    service: str = "smart-commute-optimization"
    timestamp: str


class ServiceKeyStatus(BaseModel):
    """Whether each Azure service key is configured (True/False)."""
    azure_maps_subscription_key: bool
    azure_maps_client_id: bool
    azure_communication_connection_string: bool


class ConfigResponse(BaseModel):
    """Public configuration the frontend may need.

    - ``azure_maps_client_id`` is intentionally exposed because the
      Azure Maps JS map control requires it client-side.
    - Actual secrets are **never** returned; only boolean flags
      indicating whether each secret is configured.
    """
    success: bool = True
    azure_maps_client_id: str
    azure_maps_base_url: str
    keys_configured: ServiceKeyStatus


# ---------------------------------------------------------------------------
# POST /api/commute/optimize
# ---------------------------------------------------------------------------


@router.post("/optimize", response_model=SuccessResponse)
async def optimize_commute(payload: CommuteOptimizationRequest):
    """Calculate the fastest combined drive + walk commute.

    **Request body** (JSON)::

        {
          "origin":           { "latitude": 40.5008, "longitude": -74.4474 },
          "destination":      { "latitude": 40.5230, "longitude": -74.4580 },
          "transitionPoints": [
            { "latitude": 40.5120, "longitude": -74.4510, "label": "Lot A" },
            { "latitude": 40.5170, "longitude": -74.4530, "label": "Lot B" }
          ],
          "departAt": "2026-02-06T08:00:00-05:00"
        }

    **Success response** (200)::

        { "success": true, "data": { ... CommuteOptimizationResult ... } }

    **Error response** (4xx / 5xx)::

        { "success": false, "error": { "message": "..." } }
    """
    try:
        result = await compute_fastest_commute(payload)
        return SuccessResponse(data=result)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# GET /api/commute/health
# ---------------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Lightweight health-check endpoint."""
    return HealthResponse(
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# GET /api/commute/config
# ---------------------------------------------------------------------------


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """Return public configuration the frontend needs.

    * ``azure_maps_client_id`` -- required by the Azure Maps JS SDK to
      initialise the map control.
    * ``azure_maps_base_url`` -- the base REST URL used for tile
      requests, etc.
    * ``keys_configured`` -- boolean flags so the frontend can show a
      meaningful status indicator without ever seeing the actual secrets.
    """
    return ConfigResponse(
        azure_maps_client_id=settings.azure_maps_client_id,
        azure_maps_base_url=settings.azure_maps_base_url,
        keys_configured=ServiceKeyStatus(
            azure_maps_subscription_key=bool(
                settings.azure_maps_subscription_key
            ),
            azure_maps_client_id=bool(settings.azure_maps_client_id),
            azure_communication_connection_string=bool(
                settings.azure_communication_connection_string
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Simple route finding (Legacy support / Single route)
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
    # Use settings instead of raw env var
    if not settings.azure_maps_subscription_key:
        raise HTTPException(status_code=500, detail="Azure Maps key not configured")
    
    url = f"{settings.azure_maps_base_url}/route/directions/json"
    params = {
        "api-version": "1.0",
        "subscription-key": settings.azure_maps_subscription_key,
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
