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
BACKGROUND_IMAGE = "/Users/srini/.gemini/antigravity/brain/903a54f8-7d21-4c32-83df-ff2c7002b0f4/realistic_parking_lot_scene_1770437612059.png"
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
        self.id = random.randint(100, 999)

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
    print("🚀 Starting RuParked AI VISION - LIVE REPLICA...")
    
    # Load background
    base_frame = cv2.imread(BACKGROUND_IMAGE)
    if base_frame is None:
        print(f"❌ Error: Could not load background image at {BACKGROUND_IMAGE}")
        return

    # Load Spots
    try:
        with open(ZONES_FILE, 'r') as f:
            spots_json = json.load(f)
        print(f"✅ Loaded {len(spots_json)} spots")
    except Exception as e:
        print(f"❌ Error loading zones: {e}")
        return

    cv2.namedWindow("RUParked", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("RUParked", 1280, 800)

    # Scaling
    h_bg, w_bg = base_frame.shape[:2]
    scale_x, scale_y = w_bg / 1920.0, h_bg / 1080.0
    
    # Simulation State
    # Screenshot: 10 occupied initially
    occupied_indices = set([1, 5, 12, 16, 25, 30, 35, 40, 45, 46])
    moving_cars = []
    
    last_backend_push = 0
    last_spawn = 0

    while True:
        frame = base_frame.copy()
        current_time = time.time()
        
        # 1. Spawn a car traversing the lot occasionally
        if current_time - last_spawn > 4 and random.random() < 0.3:
            # Spawn at top or bottom
            side = random.choice(['top', 'bottom', 'left', 'right'])
            if side == 'top': x, y, dx, dy = random.randint(100, w_bg-100), 0, random.randint(0, w_bg), h_bg
            elif side == 'bottom': x, y, dx, dy = random.randint(100, w_bg-100), h_bg, random.randint(0, w_bg), 0
            elif side == 'left': x, y, dx, dy = 0, random.randint(200, h_bg-200), w_bg, random.randint(200, h_bg-200)
            else: x, y, dx, dy = w_bg, random.randint(200, h_bg-200), 0, random.randint(200, h_bg-200)
            
            moving_cars.append(MovingCar(x, y, dx, dy, random.uniform(3, 7), f"CAR-{random.randint(10, 99)}"))
            last_spawn = current_time

        # 2. Update Backend
        if current_time - last_backend_push > 2:
            # Randomly toggle some spots to simulate movement
            if random.random() < 0.2:
                idx = random.randint(0, len(spots_json)-1)
                if idx in occupied_indices: occupied_indices.remove(idx)
                else: occupied_indices.add(idx)
            
            try:
                detections = [{"lot_name": "Yellow Lot", "spot_id": f"S{i+1}", "is_occupied": i in occupied_indices, "confidence": 0.98} for i in range(len(spots_json))]
                requests.post(BACKEND_API_URL, json={"detections": detections, "camera_id": "live-tracking-replica"}, timeout=0.1)
                last_backend_push = current_time
            except: pass

        # 3. Draw Overlays
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

        # 4. Draw Traffic & Tracking Boxes
        active_moving = []
        for car in moving_cars:
            car.update()
            if car.active:
                x, y = int(car.x), int(car.y)
                # Drawing Tracker Box (matches user's screenshot style)
                cv2.rectangle(frame, (x-40, y-30), (x+40, y+30), (255, 100, 0), 2)
                # Label box - BLUE background
                cv2.rectangle(frame, (x-40, y-50), (x+40, y-30), (255, 100, 0), -1)
                cv2.putText(frame, car.label, (x-35, y-35), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                # Motion Vector
                cv2.line(frame, (x, y), (x + int((car.dest_x - car.x)*0.05), y + int((car.dest_y - car.y)*0.05)), (0, 255, 255), 2)
                active_moving.append(car)
        moving_cars = active_moving

        # 5. Header Stats (matches Screenshot exactly)
        total = len(spots_json)
        occ = len(occupied_indices)
        avail = total - occ
        percent = int((avail / total) * 100)
        
        cv2.rectangle(frame, (0, 0), (w_bg, 85), (40, 40, 40), -1)
        cv2.putText(frame, "RUParked [LOADED]", (25, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
        cv2.putText(frame, f"TOTAL: {total}", (25, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"AVAILABLE: {avail}", (230, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, f"OCCUPIED: {occ}", (480, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Big % Indicator
        cv2.putText(frame, f"{percent}% FREE", (w_bg-240, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)

        # Footer Analysis
        cv2.putText(frame, f"Vehicles detected: {occ + len(moving_cars)}", (25, h_bg-40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        next_upd = 5 - (int(current_time) % 6)
        cv2.putText(frame, f"Next update: {next_upd}s", (w_bg-250, h_bg-40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        # Scanner Line
        scan_y = int((current_time * 300) % h_bg)
        cv2.line(frame, (0, scan_y), (w_bg, scan_y), (255, 255, 0), 1)

        # Final Blend
        frame = cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)
        cv2.imshow("RUParked", frame)
        
        if cv2.waitKey(20) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
