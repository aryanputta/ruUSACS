import cv2
import json
import time
import requests
import numpy as np
import os
import random
from pathlib import Path

# Configuration
BACKEND_API_URL = "http://localhost:4000/cv/detect/batch"
VIDEO_PATH = "/Users/srini/Downloads/ruUSACS-main/vision/live_parking_video.mp4"
ZONES_FILE = "/Users/srini/Downloads/ruUSACS-main/vision/manual_parking_zone.json"

class Car:
    def __init__(self, id, start_pos, end_pos, speed, type="parking", spot_idx=None):
        self.id = id
        self.x, self.y = float(start_pos[0]), float(start_pos[1])
        self.dest_x, self.dest_y = float(end_pos[0]), float(end_pos[1])
        self.speed = speed
        self.type = type # "parking", "leaving", "traversal"
        self.spot_idx = spot_idx
        self.active = True
        self.path = []
        self.color = (255, 120, 0) if type == "parking" else (0, 165, 255) # Orange for parking, Blue for traversal/leaving

    def update(self):
        self.path.append((int(self.x), int(self.y)))
        if len(self.path) > 30: self.path.pop(0)
        
        dx = self.dest_x - self.x
        dy = self.dest_y - self.y
        dist = np.sqrt(dx**2 + dy**2)
        
        if dist < self.speed:
            self.active = False
            return True # Target reached
        
        self.x += (dx / dist) * self.speed
        self.y += (dy / dist) * self.speed
        return False

    def get_bbox(self):
        return (int(self.x - 35), int(self.y - 25), int(self.x + 35), int(self.y + 25))

def main():
    print("🚀 Starting RUParked AI VISION - DYNAMIC BLUE TRACKER...")
    
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ Error: Video not found at {VIDEO_PATH}")
        return

    try:
        with open(ZONES_FILE, 'r') as f:
            spots_json = json.load(f)
        print(f"✅ Loaded {len(spots_json)} spots")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    cap = cv2.VideoCapture(VIDEO_PATH)
    cv2.namedWindow("RUParked AI Vision", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("RUParked AI Vision", 1280, 720)

    # Initial Global State
    occupied_indices = set(random.sample(range(len(spots_json)), 15))
    cars = []
    last_action_time = 0
    last_push_time = 0
    car_id_counter = 5000

    def push_update(transient_occupied=None):
        if transient_occupied is None: transient_occupied = set()
        try:
            detections = []
            for i in range(len(spots_json)):
                is_occ = (i in occupied_indices) or (i in transient_occupied)
                detections.append({
                    "lot_name": "Yellow Lot", 
                    "spot_id": f"S{i+1}", 
                    "is_occupied": is_occ, 
                    "confidence": 0.99 if i in occupied_indices else 0.85
                })
            requests.post(BACKEND_API_URL, json={"detections": detections, "camera_id": "dynamic-tracker"}, timeout=0.1)
        except: pass

    points_of_entry = [(0, 540), (1920, 540), (960, 0), (960, 1080)]

    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
            
        h, w = frame.shape[:2]
        scale_x, scale_y = w / 1920.0, h / 1080.0
        current_time = time.time()

        # 1. Action Logic
        if current_time - last_action_time > 4: # Faster events
            rand = random.random()
            if rand < 0.3: # Park
                available = [i for i in range(len(spots_json)) if i not in occupied_indices]
                if available:
                    idx = random.choice(available)
                    start = random.choice(points_of_entry)
                    dest = (spots_json[idx]["center"][0] * scale_x, spots_json[idx]["center"][1] * scale_y)
                    cars.append(Car(f"PK-{car_id_counter}", (start[0]*scale_x, start[1]*scale_y), dest, random.uniform(7, 12), "parking", idx))
            elif rand < 0.6: # Leave
                if occupied_indices:
                    idx = random.choice(list(occupied_indices))
                    start = (spots_json[idx]["center"][0] * scale_x, spots_json[idx]["center"][1] * scale_y)
                    dest = random.choice(points_of_entry)
                    cars.append(Car(f"LV-{car_id_counter}", start, (dest[0]*scale_x, dest[1]*scale_y), random.uniform(7, 12), "leaving", idx))
                    occupied_indices.remove(idx)
            else: # Traversal (Moving past spots)
                start = random.choice(points_of_entry)
                dest = random.choice(points_of_entry)
                while dest == start: dest = random.choice(points_of_entry)
                cars.append(Car(f"TR-{car_id_counter}", (start[0]*scale_x, start[1]*scale_y), (dest[0]*scale_x, dest[1]*scale_y), random.uniform(8, 14), "traversal"))
            
            car_id_counter += 1
            last_action_time = current_time

        # 2. Update and Detect Transients
        active_cars = []
        transient_occupied = set()
        for car in cars:
            arrived = car.update()
            
            # Intersection check - if car is over any spot
            for i, spot in enumerate(spots_json):
                sc = (spot["center"][0] * scale_x, spot["center"][1] * scale_y)
                if abs(car.x - sc[0]) < 50 and abs(car.y - sc[1]) < 40:
                    transient_occupied.add(i)
            
            if arrived:
                if car.type == "parking":
                    occupied_indices.add(car.spot_idx)
            else:
                active_cars.append(car)
        cars = active_cars

        # 3. Always push if transients detected or on interval
        if transient_occupied or current_time - last_push_time > 1:
            push_update(transient_occupied)
            last_push_time = current_time

        # 4. Drawing
        overlay = frame.copy()
        for i, spot in enumerate(spots_json):
            pts = (np.array(spot["points"], dtype=np.float32) * [scale_x, scale_y]).astype(np.int32)
            is_occ = (i in occupied_indices) or (i in transient_occupied)
            color = (0, 0, 255) if is_occ else (0, 255, 0)
            cv2.polylines(frame, [pts], True, color, 1)
            cv2.fillPoly(overlay, [pts], color)
        
        for car in cars:
            x, y = int(car.x), int(car.y)
            # Trail
            for j in range(len(car.path)-1):
                cv2.line(frame, car.path[j], car.path[j+1], car.color, 2)
            
            # Tracker Box (Blue for traversal, Orange for parking)
            cv2.rectangle(frame, (x-35, y-25), (x+35, y+25), car.color, 2)
            cv2.putText(frame, f"{car.id}", (x-35, y-35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.drawMarker(frame, (x, y), car.color, cv2.MARKER_TILTED_CROSS, 15, 2)

        # Presentation Header
        cv2.rectangle(frame, (0, 0), (w, 60), (30, 30, 30), -1)
        cv2.putText(frame, "RUParked [DYNAMIC DUAL-LAYER TRACKING]", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, f"LIVE: {len(cars)} VEHICLES | {len(occupied_indices)} PARKED", (w-450, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, car.color if cars else (0, 255, 0), 1)

        frame = cv2.addWeighted(overlay, 0.15, frame, 0.85, 0)
        cv2.imshow("RUParked AI Vision", frame)
        if cv2.waitKey(20) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
