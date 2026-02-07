"""
REST routes for the Smart Commute Optimization API.

All functionality is exposed as HTTP endpoints so the frontend never
needs direct access to Azure services or keys.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.navigation.optimization import (
    CommuteOptimizationRequest,
    CommuteOptimizationResult,
    compute_fastest_commute,
)

router = APIRouter(prefix="/api/commute", tags=["commute"])


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
