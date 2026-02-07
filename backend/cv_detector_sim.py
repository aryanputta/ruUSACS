"""
CV Parking Detector Simulator
Simulates a computer vision model detecting parking spots from camera feeds.
This runs independently and sends detection data to the backend API.
"""
import asyncio
import random
import httpx
from datetime import datetime
from typing import List, Dict

# Configuration
BACKEND_URL = "http://localhost:4000"
UPDATE_INTERVAL = 5  # seconds between updates

# Parking lot definitions (simulating camera coverage)
PARKING_LOTS = {
    "LOT_A": {
        "campus": "BUSCH",
        "total_spots": 45,
        "rows": 5,
        "cols": 9,
        "base_occupancy": 0.73  # 73% average occupancy
    },
    "LOT_B": {
        "campus": "BUSCH", 
        "total_spots": 50,
        "rows": 5,
        "cols": 10,
        "base_occupancy": 0.94  # Very busy lot
    },
    "LOT_C": {
        "campus": "BUSCH",
        "total_spots": 60,
        "rows": 6,
        "cols": 10,
        "base_occupancy": 0.53  # Good availability
    },
    "LOT_D": {
        "campus": "COLLEGE_AVE",
        "total_spots": 35,
        "rows": 5,
        "cols": 7,
        "base_occupancy": 0.77
    }
}

# Current spot states
spot_states: Dict[str, Dict[str, bool]] = {}


def initialize_spots():
    """Initialize parking spots with realistic distribution."""
    for lot_name, config in PARKING_LOTS.items():
        spot_states[lot_name] = {}
        total = config["total_spots"]
        occupied_target = int(total * config["base_occupancy"])
        
        # Create all spots
        for i in range(total):
            row = i // config["cols"] + 1
            col = i % config["cols"] + 1
            spot_id = f"R{row}C{col}"
            spot_states[lot_name][spot_id] = False
        
        # Randomly occupy spots
        spot_ids = list(spot_states[lot_name].keys())
        random.shuffle(spot_ids)
        for spot_id in spot_ids[:occupied_target]:
            spot_states[lot_name][spot_id] = True


def simulate_changes():
    """Simulate cars arriving and leaving."""
    changes = []
    
    for lot_name, spots in spot_states.items():
        # Calculate current occupancy
        occupied = sum(1 for s in spots.values() if s)
        total = len(spots)
        
        # Randomly change 0-3 spots per lot
        num_changes = random.randint(0, 3)
        spot_ids = list(spots.keys())
        random.shuffle(spot_ids)
        
        for spot_id in spot_ids[:num_changes]:
            # Tendency to maintain base occupancy
            base_occ = PARKING_LOTS[lot_name]["base_occupancy"]
            current_occ = occupied / total
            
            # If above target, more likely to free spots
            if current_occ > base_occ:
                new_state = random.random() < 0.3  # 30% chance to be occupied
            else:
                new_state = random.random() < 0.7  # 70% chance to be occupied
            
            if spots[spot_id] != new_state:
                spots[spot_id] = new_state
                changes.append({
                    "lot_name": lot_name,
                    "spot_id": spot_id,
                    "is_occupied": new_state,
                    "confidence": round(random.uniform(0.92, 0.99), 3)
                })
    
    return changes


async def send_detections(detections: List[Dict]):
    """Send detection batch to backend API."""
    if not detections:
        return
    
    payload = {
        "detections": [
            {
                "lot_name": d["lot_name"],
                "spot_id": d["spot_id"],
                "is_occupied": d["is_occupied"],
                "confidence": d["confidence"],
                "timestamp": datetime.now().isoformat()
            }
            for d in detections
        ],
        "frame_id": f"frame_{int(datetime.now().timestamp())}",
        "camera_id": "sim_camera_1"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/cv/detect/batch",
                json=payload,
                timeout=10.0
            )
            if response.status_code == 200:
                result = response.json()
                print(f"[CV] Sent {len(detections)} detections - {result.get('spots_freed', 0)} spots freed")
            else:
                print(f"[CV] Error: {response.status_code}")
    except Exception as e:
        print(f"[CV] Connection error: {e}")


async def send_full_state():
    """Send complete parking lot state to backend."""
    all_detections = []
    
    for lot_name, spots in spot_states.items():
        for spot_id, is_occupied in spots.items():
            all_detections.append({
                "lot_name": lot_name,
                "spot_id": spot_id,
                "is_occupied": is_occupied,
                "confidence": round(random.uniform(0.95, 0.99), 3)
            })
    
    await send_detections(all_detections)


def print_status():
    """Print current parking status."""
    print("\n" + "=" * 50)
    print("CV PARKING DETECTOR STATUS")
    print("=" * 50)
    
    for lot_name, spots in spot_states.items():
        occupied = sum(1 for s in spots.values() if s)
        total = len(spots)
        available = total - occupied
        pct = round(occupied / total * 100, 1)
        
        bar_len = 20
        filled = int(pct / 100 * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        
        status = "🔴" if pct > 90 else "🟡" if pct > 70 else "🟢"
        print(f"{status} {lot_name}: {available}/{total} available [{bar}] {pct}%")
    
    print("=" * 50)


async def main():
    """Main loop for CV simulator."""
    print("\n🎥 CV Parking Detector Simulator Starting...")
    print(f"   Backend: {BACKEND_URL}")
    print(f"   Update interval: {UPDATE_INTERVAL}s\n")
    
    # Initialize spots
    initialize_spots()
    print_status()
    
    # Send initial full state
    print("\n[CV] Sending initial parking state...")
    await send_full_state()
    
    # Main loop
    print(f"\n[CV] Running continuous detection (Ctrl+C to stop)...")
    while True:
        await asyncio.sleep(UPDATE_INTERVAL)
        
        # Simulate spot changes
        changes = simulate_changes()
        
        if changes:
            await send_detections(changes)
            print_status()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[CV] Detector stopped.")
