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

def main():
    print("🚀 Starting RUParked AI VISION - CAUSAL TRACKER...")
    
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
    car_id_counter = 1000

    def push_update():
        try:
            detections = [{"lot_name": "Yellow Lot", "spot_id": f"S{i+1}", "is_occupied": i in occupied_indices, "confidence": 0.99} for i in range(len(spots_json))]
            requests.post(BACKEND_API_URL, json={"detections": detections, "camera_id": "causal-tracker"}, timeout=0.1)
        except: pass

    # Entrances/Exits (Simulated Screen Edges)
    points_of_entry = [(0, 540), (1920, 540), (960, 0), (960, 1080)]

    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
            
        h, w = frame.shape[:2]
        scale_x, scale_y = w / 1920.0, h / 1080.0
        current_time = time.time()

        # 1. Action Logic: Park or Leave
        if current_time - last_action_time > 5: # Every 5 seconds something happens
            if random.random() > 0.5: # Request Parking
                available = [i for i in range(len(spots_json)) if i not in occupied_indices]
                if available:
                    idx = random.choice(available)
                    start = random.choice(points_of_entry)
                    dest = (spots_json[idx]["center"][0] * scale_x, spots_json[idx]["center"][1] * scale_y)
                    cars.append(Car(f"IN-{car_id_counter}", (start[0]*scale_x, start[1]*scale_y), dest, random.uniform(6, 10), "parking", idx))
                    car_id_counter += 1
            else: # Request Leaving
                if occupied_indices:
                    idx = random.choice(list(occupied_indices))
                    # Mark for leaving (but don't release yet visually)
                    start = (spots_json[idx]["center"][0] * scale_x, spots_json[idx]["center"][1] * scale_y)
                    dest = random.choice(points_of_entry)
                    dest = (dest[0]*scale_x, dest[1]*scale_y)
                    cars.append(Car(f"OUT-{car_id_counter}", start, dest, random.uniform(6, 10), "leaving", idx))
                    # Release spot immediately from logic so others can take it, but visual follows car
                    occupied_indices.remove(idx)
                    push_update()
                    car_id_counter += 1
            last_action_time = current_time

        # 2. Update Cars
        active_cars = []
        for car in cars:
            arrived = car.update()
            if arrived:
                if car.type == "parking":
                    occupied_indices.add(car.spot_idx)
                    push_update()
                # If leaving, it just disappears at edge
            else:
                active_cars.append(car)
        cars = active_cars

        # 3. Regular Push Sync
        if current_time - last_push_time > 3:
            push_update()
            last_push_time = current_time

        # 4. Drawing
        overlay = frame.copy()
        
        # Parking Spots
        for i, spot in enumerate(spots_json):
            pts = (np.array(spot["points"], dtype=np.float32) * [scale_x, scale_y]).astype(np.int32)
            is_occupied = i in occupied_indices
            color = (0, 0, 255) if is_occupied else (0, 255, 0)
            cv2.polylines(frame, [pts], True, color, 1)
            cv2.fillPoly(overlay, [pts], color)
        
        # Draw Moving Cars (The "Trackers")
        for car in cars:
            x, y = int(car.x), int(car.y)
            # Trail
            for j in range(len(car.path)-1):
                cv2.line(frame, car.path[j], car.path[j+1], (0, 255, 255), 2)
            
            # Tracking Box
            box_color = (255, 120, 0) if car.type == "parking" else (0, 200, 255)
            cv2.rectangle(frame, (x-35, y-25), (x+35, y+25), box_color, 2)
            cv2.putText(frame, f"{car.id} - {car.type.upper()}", (x-35, y-35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            cv2.drawMarker(frame, (x, y), box_color, cv2.MARKER_CROSS, 20, 2)

        # UI Overlay
        cv2.rectangle(frame, (0, 0), (w, 80), (20, 20, 20), -1)
        cv2.putText(frame, "RUParked [LIVE CAUSAL ANALYSIS]", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        total = len(spots_json)
        free = total - len(occupied_indices)
        cv2.putText(frame, f"SPOTS: {total} | FREE: {free} | EVENTS: {len(cars)}", (w-350, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        
        # Scanner line
        scan_y = int((current_time * 150) % h)
        cv2.line(frame, (0, scan_y), (w, scan_y), (0, 255, 255), 1)

        # Final Blend
        frame = cv2.addWeighted(overlay, 0.15, frame, 0.85, 0)
        cv2.imshow("RUParked AI Vision", frame)
        if cv2.waitKey(30) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
