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


# ============================================================================
# LIVE BUS TRACKING
# ============================================================================

class LiveBusPosition(BaseModel):
    vehicle_id: str
    route_id: str
    route_name: str
    route_color: str
    latitude: float
    longitude: float
    heading: int  # degrees, 0=North
    speed_mph: float
    last_updated: str
    next_stop: str
    passengers: Optional[int] = None


class ParkingSpotStatus(BaseModel):
    lot_name: str
    spot_id: str
    is_occupied: bool
    last_updated: str
    spot_type: str  # "regular", "handicap", "ev_charging"


@router.get("/live/buses", response_model=List[LiveBusPosition])
async def get_live_bus_positions():
    """Get real-time positions of all Rutgers buses.
    
    Note: For hackathon demo, returns simulated positions.
    In production, this would call the PassioGO API for live GPS data.
    """
    import random
    from datetime import datetime
    
    buses = []
    
    # Simulated bus positions for each route
    for route in RUTGERS_BUS_ROUTES:
        # Each route has 2-3 active buses
        num_buses = random.randint(2, 3)
        for i in range(num_buses):
            # Generate position near Rutgers campuses
            base_lat = 40.50 + random.uniform(-0.03, 0.03)
            base_lng = -74.45 + random.uniform(-0.02, 0.02)
            
            buses.append(LiveBusPosition(
                vehicle_id=f"RU-{random.randint(100, 999)}",
                route_id=route["route_id"],
                route_name=route["name"],
                route_color=route["color"],
                latitude=round(base_lat, 6),
                longitude=round(base_lng, 6),
                heading=random.randint(0, 359),
                speed_mph=round(random.uniform(5, 25), 1),
                last_updated=datetime.now().isoformat(),
                next_stop=random.choice(route["stops"]),
                passengers=random.randint(5, 40)
            ))
    
    return buses


@router.get("/live/buses/{route_id}", response_model=List[LiveBusPosition])
async def get_buses_on_route(route_id: str):
    """Get live positions of buses on a specific route."""
    all_buses = await get_live_bus_positions()
    return [b for b in all_buses if b.route_id == route_id]


@router.get("/live/parking", response_model=List[ParkingSpotStatus])
async def get_live_parking_status(lot_name: Optional[str] = None):
    """Get real-time parking spot availability.
    
    This endpoint is designed to be called by the CV model to report
    spot status, OR by the frontend to display current availability.
    """
    import random
    from datetime import datetime
    
    lots = [
        "Lot 48 - Livingston",
        "Lot 60 - Busch", 
        "Lot 55 - Livingston",
        "Stadium Lot",
        "Lot 67 - Busch",
        "College Ave Deck"
    ]
    
    if lot_name:
        lots = [lot_name] if lot_name in lots else []
    
    spots = []
    for lot in lots:
        # Each lot has 50-200 spots
        num_spots = random.randint(50, 200)
        occupancy_rate = random.uniform(0.6, 0.95)
        
        for i in range(min(20, num_spots)):  # Return first 20 spots per lot
            spot_type = "regular"
            if i < 3:
                spot_type = "handicap"
            elif i < 6:
                spot_type = "ev_charging"
                
            spots.append(ParkingSpotStatus(
                lot_name=lot,
                spot_id=f"{lot[:3].upper()}-{i+1:03d}",
                is_occupied=random.random() < occupancy_rate,
                last_updated=datetime.now().isoformat(),
                spot_type=spot_type
            ))
    
    return spots


@router.get("/bus-info/{route_id}")
async def get_bus_details(route_id: str):
    """Get detailed info about a specific Rutgers bus route.
    
    Includes: route description, schedule, typical travel times, 
    and which campuses it connects.
    """
    bus_info = {
        "RU_A": {
            "name": "A Bus",
            "full_name": "Route A - All Campuses Express",
            "description": "Express service connecting College Ave, Busch, and Livingston campuses",
            "color": "#E31837",
            "campuses": ["College Ave", "Busch", "Livingston"],
            "frequency_minutes": 10,
            "first_bus": "07:00",
            "last_bus": "03:00",
            "typical_loop_time": 25,
            "wheelchair_accessible": True
        },
        "RU_B": {
            "name": "B Bus",
            "full_name": "Route B - All Campuses",
            "description": "Connects all campuses with more stops than A Bus",
            "color": "#00843D",
            "campuses": ["College Ave", "Busch", "Livingston", "Cook/Douglass"],
            "frequency_minutes": 12,
            "first_bus": "07:00",
            "last_bus": "03:00",
            "typical_loop_time": 35,
            "wheelchair_accessible": True
        },
        "RU_EE": {
            "name": "EE Bus",
            "full_name": "Route EE - College Ave/Cook-Douglass",
            "description": "Connects College Ave and Cook/Douglass campuses",
            "color": "#FFC72C",
            "campuses": ["College Ave", "Cook/Douglass"],
            "frequency_minutes": 8,
            "first_bus": "07:00",
            "last_bus": "23:00",
            "typical_loop_time": 15,
            "wheelchair_accessible": True
        },
        "RU_F": {
            "name": "F Bus",
            "full_name": "Route F - Busch Campus",
            "description": "Internal Busch campus circulation",
            "color": "#0073CF",
            "campuses": ["Busch"],
            "frequency_minutes": 6,
            "first_bus": "07:00",
            "last_bus": "22:00",
            "typical_loop_time": 10,
            "wheelchair_accessible": True
        },
        "RU_H": {
            "name": "H Bus",
            "full_name": "Route H - Henderson/Busch/Livingston",
            "description": "Connects Henderson apartments to Busch and Livingston",
            "color": "#6A2A8E",
            "campuses": ["Busch", "Livingston"],
            "frequency_minutes": 15,
            "first_bus": "07:00",
            "last_bus": "22:00",
            "typical_loop_time": 20,
            "wheelchair_accessible": True
        },
        "RU_LX": {
            "name": "LX Bus",
            "full_name": "Route LX - Livingston Express",
            "description": "Internal Livingston campus circulation",
            "color": "#FF6600",
            "campuses": ["Livingston"],
            "frequency_minutes": 8,
            "first_bus": "07:00",
            "last_bus": "22:00",
            "typical_loop_time": 8,
            "wheelchair_accessible": True
        },
        "RU_REXL": {
            "name": "REXL Bus",
            "full_name": "Route REXL - Livingston to Busch Express",
            "description": "Direct express between Livingston and Busch",
            "color": "#CC0000",
            "campuses": ["Livingston", "Busch"],
            "frequency_minutes": 5,
            "first_bus": "07:30",
            "last_bus": "22:00",
            "typical_loop_time": 8,
            "wheelchair_accessible": True
        },
        "RU_REXB": {
            "name": "REXB Bus",
            "full_name": "Route REXB - Busch to Livingston Express",
            "description": "Direct express between Busch and Livingston",
            "color": "#CC0000",
            "campuses": ["Busch", "Livingston"],
            "frequency_minutes": 5,
            "first_bus": "07:30",
            "last_bus": "22:00",
            "typical_loop_time": 8,
            "wheelchair_accessible": True
        }
    }
    
    if route_id not in bus_info:
        raise HTTPException(status_code=404, detail="Route not found")
    
    info = bus_info[route_id]
    
    # Add live bus count
    live_buses = await get_buses_on_route(route_id)
    info["active_buses"] = len(live_buses)
    info["live_positions"] = live_buses
    
    return info

