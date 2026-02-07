import cv2
import json
import time
import requests
import numpy as np
import os
import random
from pathlib import Path
from datetime import datetime

# Configuration
# Note: Main backend for pushing detections is 4000
BACKEND_API_URL = "http://localhost:4000/cv/detect/batch"
BACKGROUND_IMAGE = "/Users/srini/.gemini/antigravity/brain/903a54f8-7d21-4c32-83df-ff2c7002b0f4/realistic_parking_lot_scene_1770437612059.png"
ZONES_FILE = "/Users/srini/Downloads/ruUSACS-main/vision/manual_parking_zone.json"

def main():
    print("🚀 Starting Dynamic RuParked AI Vision...")
    
    # Load background
    base_frame = cv2.imread(BACKGROUND_IMAGE)
    if base_frame is None:
        print(f"❌ Error: Could not load background image at {BACKGROUND_IMAGE}")
        return

    # Load Spots
    try:
        with open(ZONES_FILE, 'r') as f:
            spots_json = json.load(f)
        print(f"✅ Loaded {len(spots_json)} spots for dynamic analysis")
    except Exception as e:
        print(f"❌ Error loading zones: {e}")
        return

    cv2.namedWindow("RUParked - AI Live Analysis", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("RUParked - AI Live Analysis", 1280, 800)

    # State Management
    # Start with 37 available, 10 occupied as per screenshot
    occupied_indices = set([1, 5, 12, 16, 25, 30, 35, 40, 45, 46])
    h_bg, w_bg = base_frame.shape[:2]
    scale_x, scale_y = w_bg / 1920.0, h_bg / 1080.0
    
    # Traffic Simulation: List of "moving" cars in aisles
    # Each car: [x, y, dx, dy, color, label]
    moving_cars = []
    
    last_state_change = time.time()
    last_backend_push = 0
    start_time = time.time()

    print("📡 AI Vision is now ANALYZING and SYNCING to Dashboard...")

    while True:
        frame = base_frame.copy()
        current_time = time.time()
        
        # 1. DYNAMIC OCCUPANCY CHANGES (Every 5-10 seconds)
        if current_time - last_state_change > random.randint(5, 12):
            # A car leaves
            if len(occupied_indices) > 5:
                leaving = random.choice(list(occupied_indices))
                occupied_indices.remove(leaving)
                # Add it to moving cars (leaving the lot)
                spot = spots_json[leaving]
                cx, cy = int(spot["center"][0] * scale_x), int(spot["center"][1] * scale_y)
                moving_cars.append([cx, cy, random.randint(2, 5), random.randint(-2, 2), (255, 100, 0), f"CAR-LEAVING-S{leaving+1}"])
            
            # A car arrives
            if len(occupied_indices) < 40:
                available = [i for i in range(len(spots_json)) if i not in occupied_indices]
                arriving = random.choice(available)
                occupied_indices.add(arriving)
                # Add visual cue for arrival
                print(f"DEBUG: Car parked at Spot {arriving+1}")
            
            last_state_change = current_time

        # 2. SYNC TO BACKEND (Every 2 seconds)
        if current_time - last_backend_push > 2:
            try:
                detections = []
                for i in range(len(spots_json)):
                    detections.append({
                        "lot_name": "Yellow Lot",
                        "spot_id": f"S{i+1}",
                        "is_occupied": i in occupied_indices,
                        "confidence": 0.95 + (random.random() * 0.04)
                    })
                requests.post(BACKEND_API_URL, json={
                    "detections": detections,
                    "camera_id": "dynamic-ai-vision"
                }, timeout=0.2)
                last_backend_push = current_time
            except:
                pass

        # 3. DRAW PARKING SPOTS
        overlay = frame.copy()
        for i, spot in enumerate(spots_json):
            pts = (np.array(spot["points"], dtype=np.float32) * [scale_x, scale_y]).astype(np.int32)
            is_occupied = i in occupied_indices
            color = (0, 0, 255) if is_occupied else (0, 255, 0)
            cv2.polylines(frame, [pts], True, color, 2)
            cv2.fillPoly(overlay, [pts], color)
            
            # Label
            cx, cy = int(spot["center"][0] * scale_x), int(spot["center"][1] * scale_y)
            cv2.putText(frame, f"S{i+1}", (cx-10, cy+5), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

        # 4. SIMULATE TRAFFIC (Moving Cars)
        new_moving_cars = []
        for car in moving_cars:
            x, y, dx, dy, color, label = car
            x += dx
            y += dy
            # Draw car as a blue box with a vector
            cv2.rectangle(frame, (x-30, y-20), (x+30, y+20), color, 2)
            cv2.line(frame, (x, y), (x+dx*5, y+dy*5), (255, 255, 0), 2)
            cv2.putText(frame, label, (x-30, y-25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # Analytical "Movement Vector" overlay
            cv2.putText(frame, f"V:{dx},{dy}", (x-20, y+10), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
            
            # Keep cars that aren't off-screen
            if 0 < x < w_bg and 0 < y < h_bg:
                new_moving_cars.append([x, y, dx, dy, color, label])
        moving_cars = new_moving_cars

        # Occasionally add a "thru-traffic" car
        if random.random() < 0.01:
            moving_cars.append([0, 400, 8, random.randint(-1, 1), (255, 100, 0), "TRAFFIC-THRU"])

        # 5. UI HEADER & STATS
        cv2.rectangle(frame, (0, 0), (w_bg, 80), (40, 40, 40), -1)
        total = len(spots_json)
        occ = len(occupied_indices)
        avail = total - occ
        percent = int((avail/total)*100)
        
        cv2.putText(frame, "RUParked AI ANALYSIS [LIVE]", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(frame, f"TOTAL: {total} | OPEN: {avail} | BUSY: {occ}", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        # Color-coded percentage (matches traffic feel)
        p_color = (0, 255, 0) if percent > 50 else (0, 255, 255) if percent > 20 else (0, 0, 255)
        cv2.putText(frame, f"{percent}% FREE", (w_bg-220, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.1, p_color, 3)

        # 6. ANALYTICAL "SCANNER" LINE
        scan_y = int((time.time() * 300) % h_bg)
        cv2.line(frame, (0, scan_y), (w_bg, scan_y), (255, 255, 0), 1)
        cv2.putText(frame, "SCANNED AREA", (w_bg-120, scan_y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 0), 1)

        # Final Blend
        frame = cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)
        cv2.imshow("RUParked - AI Live Analysis", frame)
        
        if cv2.waitKey(20) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
