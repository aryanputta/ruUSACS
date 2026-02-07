"""
Smart Commute Optimization -- Fastest Total Commute (Drive + Walk)

Uses the Azure Maps Route Matrix API to evaluate multi-modal commute
options.  Given an origin, a destination, and a set of candidate
transition points (e.g. parking lots, transit stops), the service:

  1. Requests a driving route-matrix from the origin to every
     candidate transition point.
  2. Requests a walking route-matrix from every candidate transition
     point to the final destination.
  3. Combines the two legs and returns the transition point that
     yields the shortest *total* travel time, along with full
     summary data for both legs.

All Azure Maps credentials stay on the server -- the frontend only
interacts through the REST API exposed in /routes.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

from backend.config import settings

# ---------------------------------------------------------------------------
# Pydantic models (replace TypeScript interfaces)
# ---------------------------------------------------------------------------


class GeoPoint(BaseModel):
    """A geographic coordinate (latitude / longitude)."""

    latitude: float
    longitude: float


class TransitionPoint(GeoPoint):
    """A candidate transition point with an optional human-readable label."""

    label: Optional[str] = None


class RouteLegSummary(BaseModel):
    """Summary for a single route leg returned by Azure Maps."""

    travel_time_in_seconds: int = Field(
        ..., description="Travel time in seconds."
    )
    length_in_meters: int = Field(..., description="Distance in metres.")
    departure_time: Optional[str] = Field(
        None, description="ISO-8601 departure time (when available)."
    )
    arrival_time: Optional[str] = Field(
        None, description="ISO-8601 arrival time (when available)."
    )


class TransitionCandidate(BaseModel):
    """A candidate transition point with the combined commute analysis."""

    point: GeoPoint
    label: Optional[str] = None
    drive_leg: RouteLegSummary
    walk_leg: RouteLegSummary
    total_travel_time_in_seconds: int
    total_length_in_meters: int


class CommuteOptimizationRequest(BaseModel):
    """Input payload for the optimisation request."""

    origin: GeoPoint
    destination: GeoPoint
    transition_points: list[TransitionPoint] = Field(
        ..., min_length=1, alias="transitionPoints"
    )
    depart_at: Optional[str] = Field(None, alias="departAt")

    model_config = {"populate_by_name": True}


class CommuteOptimizationResult(BaseModel):
    """Full response returned by the optimisation service."""

    origin: GeoPoint
    destination: GeoPoint
    best: TransitionCandidate
    candidates: list[TransitionCandidate]


# ---------------------------------------------------------------------------
# Azure Maps Route Matrix helpers
# ---------------------------------------------------------------------------

_MAX_SAFE_INTEGER = sys.maxsize


async def _fetch_route_matrix(
    client: httpx.AsyncClient,
    origins: list[GeoPoint],
    destinations: list[GeoPoint],
    travel_mode: str,
    depart_at: Optional[str] = None,
) -> dict[str, Any]:
    """Call the Azure Maps **Post Route Matrix Sync** endpoint.

    Parameters
    ----------
    client:
        Shared ``httpx.AsyncClient`` for connection pooling.
    origins:
        List of origin coordinates.
    destinations:
        List of destination coordinates.
    travel_mode:
        ``"car"`` or ``"pedestrian"``.
    depart_at:
        Optional ISO-8601 departure time for traffic-aware routing.

    Returns
    -------
    dict
        The parsed JSON response from Azure Maps.
    """
    url = f"{settings.azure_maps_base_url}/route/matrix/sync/json"

    params: dict[str, str] = {
        "api-version": "1.0",
        "subscription-key": settings.azure_maps_subscription_key,
        "travelMode": travel_mode,
        "routeType": "fastest",
    }
    if depart_at:
        params["departAt"] = depart_at

    body = {
        "origins": {
            "type": "MultiPoint",
            "coordinates": [
                [p.longitude, p.latitude] for p in origins
            ],
        },
        "destinations": {
            "type": "MultiPoint",
            "coordinates": [
                [p.longitude, p.latitude] for p in destinations
            ],
        },
    }

    response = await client.post(url, params=params, json=body)

    if response.status_code != 200:
        raise RuntimeError(
            f"Azure Maps Route Matrix API returned "
            f"{response.status_code}: {response.text}"
        )

    return response.json()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_unreachable_candidate(
    tp: TransitionPoint,
) -> TransitionCandidate:
    """Return a candidate with max-safe values so it sorts to the end."""
    unreachable = RouteLegSummary(
        travel_time_in_seconds=_MAX_SAFE_INTEGER,
        length_in_meters=_MAX_SAFE_INTEGER,
    )
    return TransitionCandidate(
        point=GeoPoint(latitude=tp.latitude, longitude=tp.longitude),
        label=tp.label,
        drive_leg=unreachable,
        walk_leg=unreachable,
        total_travel_time_in_seconds=_MAX_SAFE_INTEGER,
        total_length_in_meters=_MAX_SAFE_INTEGER,
    )


# ---------------------------------------------------------------------------
# Core optimisation logic
# ---------------------------------------------------------------------------


async def compute_fastest_commute(
    request: CommuteOptimizationRequest,
) -> CommuteOptimizationResult:
    """Compute the fastest combined drive + walk commute.

    The algorithm fans out two route-matrix requests in parallel:

    * Drive matrix: origin  -> each transition point
    * Walk matrix:  each transition point -> destination

    It then zips the results per transition point, sums the travel
    times, and selects the candidate with the lowest total.
    """
    origin = request.origin
    destination = request.destination
    transition_points = request.transition_points
    depart_at = request.depart_at

    async with httpx.AsyncClient(timeout=30.0) as client:
        drive_matrix_coro = _fetch_route_matrix(
            client, [origin], transition_points, "car", depart_at
        )
        walk_matrix_coro = _fetch_route_matrix(
            client, transition_points, [destination], "pedestrian", depart_at
        )

        drive_matrix, walk_matrix = await asyncio.gather(
            drive_matrix_coro, walk_matrix_coro
        )

    # The drive matrix has 1 origin row and N destination columns.
    drive_row: list[dict[str, Any]] = drive_matrix.get("matrix", [[]])[0]
    # The walk matrix has N origin rows, each with 1 destination column.
    walk_rows: list[list[dict[str, Any]]] = walk_matrix.get("matrix", [])

    candidates: list[TransitionCandidate] = []

    for idx, tp in enumerate(transition_points):
        # Drive leg -- origin -> transition point (row 0, col idx)
        drive_cell = drive_row[idx] if idx < len(drive_row) else None
        drive_summary = _extract_summary(drive_cell)
        if drive_summary is None:
            candidates.append(_build_unreachable_candidate(tp))
            continue

        # Walk leg -- transition point -> destination (row idx, col 0)
        walk_cell = (
            walk_rows[idx][0]
            if idx < len(walk_rows) and len(walk_rows[idx]) > 0
            else None
        )
        walk_summary = _extract_summary(walk_cell)
        if walk_summary is None:
            candidates.append(_build_unreachable_candidate(tp))
            continue

        drive_leg = RouteLegSummary(
            travel_time_in_seconds=drive_summary["travelTimeInSeconds"],
            length_in_meters=drive_summary["lengthInMeters"],
            departure_time=drive_summary.get("departureTime"),
            arrival_time=drive_summary.get("arrivalTime"),
        )
        walk_leg = RouteLegSummary(
            travel_time_in_seconds=walk_summary["travelTimeInSeconds"],
            length_in_meters=walk_summary["lengthInMeters"],
            departure_time=walk_summary.get("departureTime"),
            arrival_time=walk_summary.get("arrivalTime"),
        )

        candidates.append(
            TransitionCandidate(
                point=GeoPoint(
                    latitude=tp.latitude, longitude=tp.longitude
                ),
                label=tp.label,
                drive_leg=drive_leg,
                walk_leg=walk_leg,
                total_travel_time_in_seconds=(
                    drive_leg.travel_time_in_seconds
                    + walk_leg.travel_time_in_seconds
                ),
                total_length_in_meters=(
                    drive_leg.length_in_meters + walk_leg.length_in_meters
                ),
            )
        )

    # Sort ascending by total travel time.
    candidates.sort(key=lambda c: c.total_travel_time_in_seconds)

    return CommuteOptimizationResult(
        origin=origin,
        destination=destination,
        best=candidates[0],
        candidates=candidates,
    )


def _extract_summary(
    cell: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Safely extract the routeSummary dict from a matrix cell."""
    if cell is None:
        return None
    if cell.get("statusCode") != 200:
        return None
    return (cell.get("response") or {}).get("routeSummary")
