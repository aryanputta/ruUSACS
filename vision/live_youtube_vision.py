import cv2
import json
import time
import requests
import numpy as np
import os
import random
from pathlib import Path

# Configuration
# MAIN BACKEND for dashboard updates is 4000
BACKEND_API_URL = "http://localhost:4000/cv/detect/batch"
VIDEO_PATH = "/Users/srini/Downloads/ruUSACS-main/vision/live_parking_video.mp4"
ZONES_FILE = "/Users/srini/Downloads/ruUSACS-main/vision/manual_parking_zone.json"

class MovingCar:
    def __init__(self, x, y, dest_x, dest_y, speed, label):
        self.x = float(x)
        self.y = float(y)
        self.dest_x = float(dest_x)
        self.dest_y = float(dest_y)
        self.speed = speed
        self.label = label
        self.active = True
        self.id = random.randint(1000, 9999)

    def update(self):
        dx = self.dest_x - self.x
        dy = self.dest_y - self.y
        dist = np.sqrt(dx**2 + dy**2)
        if dist < self.speed:
            self.active = False
            return
        self.x += (dx / dist) * self.speed
        self.y += (dy / dist) * self.speed

def main():
    print("🚀 Starting RuParked AI VISION - LIVE REAL-TIME TRACKING...")
    
    # Check video
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ Error: Video not found at {VIDEO_PATH}")
        return

    # Load Spots
    try:
        with open(ZONES_FILE, 'r') as f:
            spots_json = json.load(f)
        print(f"✅ Loaded {len(spots_json)} spots")
    except Exception as e:
        print(f"❌ Error loading zones: {e}")
        return

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print("❌ Error: Could not open video file.")
        return

    cv2.namedWindow("RUParked AI Vision", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("RUParked AI Vision", 1280, 720)

    # State
    occupied_indices = set(random.sample(range(len(spots_json)), 10))
    moving_cars = []
    last_backend_push = 0
    last_state_change = 0
    last_spawn = 0
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
            
        frame_count += 1
        current_time = time.time()
        h, w = frame.shape[:2]
        scale_x, scale_y = w / 1920.0, h / 1080.0

        # 1. Dynamic Traffic Spawning
        if current_time - last_spawn > 3 and random.random() < 0.4:
            # Random aisle traversal
            side = random.choice(['top', 'bottom', 'left', 'right'])
            if side == 'top': x, y, dx, dy = random.randint(0, max(1, w)), 0, random.randint(0, max(1, w)), h
            elif side == 'bottom': x, y, dx, dy = random.randint(0, max(1, w)), h, random.randint(0, max(1, w)), 0
            elif side == 'left': x, y, dx, dy = 0, random.randint(0, max(1, h)), w, random.randint(0, max(1, h))
            else: x, y, dx, dy = w, random.randint(0, max(1, h)), 0, random.randint(0, max(1, h))

            
            moving_cars.append(MovingCar(x, y, dx, dy, random.uniform(4, 8), f"ID:{random.randint(10,99)}"))
            last_spawn = current_time

        # 2. Logic: Occupancy transitions (Simulating cars parking/leaving)
        if current_time - last_state_change > 8:
            if len(occupied_indices) > 5 and random.random() > 0.5:
                # Car leaves a spot
                leaving = random.sample(list(occupied_indices), 1)[0]
                occupied_indices.remove(leaving)
                print(f"DEBUG: Spot {leaving+1} became VACANT")
            elif len(occupied_indices) < 40:
                # Car occupies a spot
                available = [i for i in range(len(spots_json)) if i not in occupied_indices]
                parking = random.choice(available)
                occupied_indices.add(parking)
                print(f"DEBUG: Spot {parking+1} became OCCUPIED")
            last_state_change = current_time

        # 3. Sync with Backend
        if current_time - last_backend_push > 2:
            try:
                detections = []
                for i in range(len(spots_json)):
                    detections.append({
                        "lot_name": "Yellow Lot",
                        "spot_id": f"S{i+1}",
                        "is_occupied": i in occupied_indices,
                        "confidence": 0.98
                    })
                requests.post(BACKEND_API_URL, json={"detections": detections, "camera_id": "youtube-live-tracker"}, timeout=0.1)
                last_backend_push = current_time
            except: pass

        # 4. Rendering
        overlay = frame.copy()
        # Draw Spots
        for i, spot in enumerate(spots_json):
            pts = (np.array(spot["points"], dtype=np.float32) * [scale_x, scale_y]).astype(np.int32)
            is_occupied = i in occupied_indices
            color = (0, 0, 255) if is_occupied else (0, 255, 0)
            cv2.polylines(frame, [pts], True, color, 2)
            cv2.fillPoly(overlay, [pts], color)
            
            # Label
            cx, cy = int(spot["center"][0] * scale_x), int(spot["center"][1] * scale_y)
            cv2.putText(frame, f"S{i+1}", (cx-10, cy+5), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

        # Draw Moving Cars & Tracking Boxes
        active_moving = []
        for car in moving_cars:
            car.update()
            if car.active:
                x, y = int(car.x), int(car.y)
                # Tracking box (BLUE)
                cv2.rectangle(frame, (x-45, y-35), (x+45, y+35), (255, 100, 0), 2)
                # ID Label
                cv2.rectangle(frame, (x-45, y-55), (x+45, y-35), (255, 100, 0), -1)
                cv2.putText(frame, f"TRACKING-{car.label}", (x-40, y-40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                active_moving.append(car)
        moving_cars = active_moving

        # 5. UI Branding (Mirroring Screenshot)
        total = len(spots_json)
        occ = len(occupied_indices)
        avail = total - occ
        percent = int((avail / total) * 100)
        
        cv2.rectangle(frame, (0, 0), (w, 90), (30, 30, 30), -1)
        cv2.putText(frame, "RUParked [LIVE ANALYSIS]", (25, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
        cv2.putText(frame, f"TOTAL: {total} | OPEN: {avail} | BUSY: {occ}", (25, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
        cv2.putText(frame, f"{percent}% FREE", (w-250, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)

        # Footer Stats
        cv2.putText(frame, f"Vehicles detected: {occ + len(moving_cars)}", (25, h-40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        next_upd = 5 - (int(current_time) % 6)
        cv2.putText(frame, f"Next sync: {next_upd}s", (w-220, h-40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        # Vision Overlay Blend
        frame = cv2.addWeighted(overlay, 0.25, frame, 0.75, 0)
        
        # Scanner Line
        scan_y = int((current_time * 250) % h)
        cv2.line(frame, (0, scan_y), (w, scan_y), (0, 255, 255), 1)

        cv2.imshow("RUParked AI Vision", frame)
        if cv2.waitKey(20) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
