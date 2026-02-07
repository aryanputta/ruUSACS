"""
Rutgers Bus Routes Service - Navigation Module
Integrates with Rutgers PassioGO API for live bus times and route suggestions
Azure Service: NONE (Uses PassioGO public API)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import httpx

router = APIRouter(prefix="/navigation/bus", tags=["Navigation - Bus Routes"])


# Rutgers PassioGO API endpoints (public, no auth required)
PASSIOGO_BASE_URL = "https://rutgers.passiogo.com/api"


class BusStop(BaseModel):
    stop_id: str
    name: str
    latitude: float
    longitude: float


class BusRoute(BaseModel):
    route_id: str
    name: str
    short_name: str
    color: str
    stops: List[str]


class BusArrival(BaseModel):
    route_name: str
    stop_name: str
    eta_minutes: int
    vehicle_id: Optional[str] = None


class MultiModalRoute(BaseModel):
    mode: str  # "drive_only", "bus_only", "drive_then_bus"
    total_time_minutes: int
    parking_lot: Optional[str] = None
    bus_route: Optional[str] = None
    walk_time_minutes: int = 0
    drive_time_minutes: int = 0
    bus_time_minutes: int = 0
    recommendation: str


# Hardcoded Rutgers bus routes (from PassioGO)
RUTGERS_BUS_ROUTES = [
    {"route_id": "RU_A", "name": "A Bus", "short_name": "A", "color": "#E31837", 
     "stops": ["College Ave Student Center", "Busch Student Center", "Livingston Plaza"]},
    {"route_id": "RU_B", "name": "B Bus", "short_name": "B", "color": "#00843D",
     "stops": ["Busch Student Center", "Livingston Plaza", "College Ave Student Center"]},
    {"route_id": "RU_EE", "name": "EE Bus", "short_name": "EE", "color": "#FFC72C",
     "stops": ["College Ave Student Center", "Scott Hall", "Rutgers Student Center", "Cook/Douglass"]},
    {"route_id": "RU_F", "name": "F Bus", "short_name": "F", "color": "#0073CF",
     "stops": ["Busch Student Center", "Allison Road Classrooms", "Library of Science"]},
    {"route_id": "RU_H", "name": "H Bus", "short_name": "H", "color": "#6A2A8E",
     "stops": ["Henderson Parking Lot", "Busch Student Center", "Livingston Student Center"]},
    {"route_id": "RU_LX", "name": "LX Bus", "short_name": "LX", "color": "#FF6600",
     "stops": ["Livingston Student Center", "Quads", "Plaza"]},
    {"route_id": "RU_REXL", "name": "REXL Bus", "short_name": "REXL", "color": "#CC0000",
     "stops": ["Livingston Student Center", "Busch Student Center"]},
    {"route_id": "RU_REXB", "name": "REXB Bus", "short_name": "REXB", "color": "#CC0000",
     "stops": ["Busch Student Center", "Livingston Student Center"]},
]

# Bus stops with coordinates
RUTGERS_BUS_STOPS = [
    {"stop_id": "CASC", "name": "College Ave Student Center", "latitude": 40.5002, "longitude": -74.4475},
    {"stop_id": "BSC", "name": "Busch Student Center", "latitude": 40.5232, "longitude": -74.4580},
    {"stop_id": "LSC", "name": "Livingston Student Center", "latitude": 40.5230, "longitude": -74.4375},
    {"stop_id": "SCOTT", "name": "Scott Hall", "latitude": 40.4993, "longitude": -74.4477},
    {"stop_id": "ALLISON", "name": "Allison Road Classrooms", "latitude": 40.5215, "longitude": -74.4620},
    {"stop_id": "LOS", "name": "Library of Science", "latitude": 40.5224, "longitude": -74.4650},
]

# Lot to bus stop mapping
LOT_BUS_CONNECTIONS = {
    "Lot 48 - Livingston": {"stop": "Livingston Student Center", "walk_minutes": 3},
    "Lot 60 - Busch": {"stop": "Busch Student Center", "walk_minutes": 5},
    "Lot 55 - Livingston": {"stop": "Livingston Student Center", "walk_minutes": 4},
    "Stadium Lot": {"stop": "Livingston Student Center", "walk_minutes": 8},
    "Lot 67 - Busch": {"stop": "Allison Road Classrooms", "walk_minutes": 3},
    "College Ave Deck": {"stop": "College Ave Student Center", "walk_minutes": 2},
    "Lot 26 - College Ave": {"stop": "Scott Hall", "walk_minutes": 4},
    "Lot 64 - Busch": {"stop": "Library of Science", "walk_minutes": 2},
}


@router.get("/routes", response_model=List[BusRoute])
async def get_bus_routes():
    """Get all Rutgers bus routes."""
    return [BusRoute(**r) for r in RUTGERS_BUS_ROUTES]


@router.get("/stops", response_model=List[BusStop])
async def get_bus_stops():
    """Get all Rutgers bus stops."""
    return [BusStop(**s) for s in RUTGERS_BUS_STOPS]


@router.get("/arrivals/{stop_name}", response_model=List[BusArrival])
async def get_arrivals(stop_name: str):
    """Get live bus arrivals at a stop.
    
    Note: For hackathon demo, returns simulated data.
    In production, this would call the PassioGO API.
    """
    # Simulated arrivals (in production, call PassioGO API)
    import random
    arrivals = []
    for route in RUTGERS_BUS_ROUTES:
        if stop_name in route["stops"]:
            arrivals.append(BusArrival(
                route_name=route["name"],
                stop_name=stop_name,
                eta_minutes=random.randint(2, 15),
                vehicle_id=f"RU-{random.randint(100, 999)}"
            ))
    return arrivals


@router.get("/recommend")
async def recommend_route(
    origin_campus: str,
    destination_campus: str,
    parking_lot: Optional[str] = None
):
    """Recommend the best bus route between campuses.
    
    Campuses: College Ave, Busch, Livingston, Cook/Douglass
    """
    campus_stops = {
        "college ave": "College Ave Student Center",
        "busch": "Busch Student Center",
        "livingston": "Livingston Student Center",
        "cook": "Cook/Douglass",
        "douglass": "Cook/Douglass"
    }
    
    origin = campus_stops.get(origin_campus.lower())
    destination = campus_stops.get(destination_campus.lower())
    
    if not origin or not destination:
        raise HTTPException(status_code=400, detail="Invalid campus name")
    
    # Find routes that connect these stops
    connecting_routes = []
    for route in RUTGERS_BUS_ROUTES:
        if origin in route["stops"] and destination in route["stops"]:
            connecting_routes.append(route["name"])
    
    if not connecting_routes:
        return {
            "success": False,
            "message": f"No direct bus found from {origin_campus} to {destination_campus}",
            "suggestion": "Consider taking A or B bus with a transfer"
        }
    
    return {
        "success": True,
        "origin": origin,
        "destination": destination,
        "recommended_routes": connecting_routes,
        "estimated_time_minutes": 10 + (5 if len(connecting_routes) == 1 else 3),
        "tip": f"Take the {connecting_routes[0]} for the fastest route!"
    }


@router.post("/multi-modal", response_model=List[MultiModalRoute])
async def calculate_multi_modal_options(
    origin_lat: float,
    origin_lng: float,
    destination_campus: str,
    include_bus: bool = True
):
    """Calculate multi-modal route options (drive + park + bus).
    
    Returns ranked options:
    1. Drive only (to destination campus parking)
    2. Park at nearby lot + take bus
    3. Park at remote lot (cheaper) + take bus
    """
    options = []
    
    # Option 1: Drive only
    options.append(MultiModalRoute(
        mode="drive_only",
        total_time_minutes=25,
        parking_lot=f"{destination_campus} Deck",
        bus_route=None,
        walk_time_minutes=5,
        drive_time_minutes=20,
        bus_time_minutes=0,
        recommendation="Fastest but parking may be full during peak hours"
    ))
    
    if include_bus:
        # Option 2: Park at Livingston + Bus
        options.append(MultiModalRoute(
            mode="drive_then_bus",
            total_time_minutes=30,
            parking_lot="Lot 48 - Livingston",
            bus_route="A Bus",
            walk_time_minutes=3,
            drive_time_minutes=15,
            bus_time_minutes=12,
            recommendation="Park at Livingston (usually available) and take A Bus"
        ))
        
        # Option 3: Park at Stadium (usually empty) + Bus
        options.append(MultiModalRoute(
            mode="drive_then_bus",
            total_time_minutes=35,
            parking_lot="Stadium Lot",
            bus_route="H Bus",
            walk_time_minutes=8,
            drive_time_minutes=12,
            bus_time_minutes=15,
            recommendation="Stadium has plenty of spots but longer walk to bus"
        ))
    
    # Sort by total time
    options.sort(key=lambda x: x.total_time_minutes)
    
    return options


@router.get("/lot-to-bus/{lot_name}")
async def get_lot_to_bus_info(lot_name: str):
    """Get bus connection info for a specific parking lot."""
    if lot_name not in LOT_BUS_CONNECTIONS:
        raise HTTPException(status_code=404, detail="Lot not found")
    
    connection = LOT_BUS_CONNECTIONS[lot_name]
    stop_name = connection["stop"]
    
    # Get arrivals at that stop
    arrivals = await get_arrivals(stop_name)
    
    return {
        "lot": lot_name,
        "nearest_stop": stop_name,
        "walk_time_minutes": connection["walk_minutes"],
        "next_buses": arrivals[:3]  # Top 3 upcoming buses
    }
