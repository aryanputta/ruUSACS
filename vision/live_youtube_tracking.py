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

class Tracker:
    def __init__(self, id, x, y, dest_x, dest_y, speed):
        self.id = id
        self.x = float(x)
        self.y = float(y)
        self.dest_x = float(dest_x)
        self.dest_y = float(dest_y)
        self.speed = speed
        self.active = True
        self.path = [] # Trail of previous positions

    def update(self):
        self.path.append((int(self.x), int(self.y)))
        if len(self.path) > 20: self.path.pop(0)
        
        dx = self.dest_x - self.x
        dy = self.dest_y - self.y
        dist = np.sqrt(dx**2 + dy**2)
        if dist < self.speed:
            self.active = False
            return
        self.x += (dx / dist) * self.speed
        self.y += (dy / dist) * self.speed

def main():
    print("🚀 Starting RUParked AI VISION - ULTIMATE TRACKER...")
    
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ Error: Video not found at {VIDEO_PATH}")
        return

    try:
        with open(ZONES_FILE, 'r') as f:
            spots_json = json.load(f)
        print(f"✅ Loaded {len(spots_json)} spots")
    except Exception as e:
        print(f"❌ Error loading zones: {e}")
        return

    cap = cv2.VideoCapture(VIDEO_PATH)
    cv2.namedWindow("RUParked AI Vision", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("RUParked AI Vision", 1280, 720)

    # State
    occupied_indices = set(random.sample(range(len(spots_json)), 12))
    trackers = []
    last_push = 0
    last_spawn = 0
    last_spot_toggle = 0
    tracker_id_counter = 100

    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
            
        h, w = frame.shape[:2]
        scale_x, scale_y = w / 1920.0, h / 1080.0
        current_time = time.time()

        # 1. Spawn "Tracking" Boxes for moving cars in aisles
        if current_time - last_spawn > 2 and len(trackers) < 8:
            # Spawn at edges, move across
            side = random.choice(['top', 'bottom', 'left', 'right'])
            if side == 'top': x, y, dx, dy = random.randint(0, w), 0, random.randint(0, w), h
            elif side == 'bottom': x, y, dx, dy = random.randint(0, w), h, random.randint(0, w), 0
            elif side == 'left': x, y, dx, dy = 0, random.randint(0, h), w, random.randint(0, h)
            else: x, y, dx, dy = w, random.randint(0, h), 0, random.randint(0, h)
            
            trackers.append(Tracker(f"TR-{tracker_id_counter}", x, y, dx, dy, random.uniform(5, 10)))
            tracker_id_counter += 1
            last_spawn = current_time

        # 2. Simulate Parking/Leaving
        if current_time - last_spot_toggle > 10:
            if random.random() > 0.5 and len(occupied_indices) > 5:
                occupied_indices.remove(random.choice(list(occupied_indices)))
            elif len(occupied_indices) < 40:
                available = [i for i in range(len(spots_json)) if i not in occupied_indices]
                occupied_indices.add(random.choice(available))
            last_spot_toggle = current_time

        # 3. Sync to Dashboard
        if current_time - last_push > 2:
            try:
                detections = [{"lot_name": "Yellow Lot", "spot_id": f"S{i+1}", "is_occupied": i in occupied_indices, "confidence": 0.98} for i in range(len(spots_json))]
                requests.post(BACKEND_API_URL, json={"detections": detections, "camera_id": "ultimate-tracker"}, timeout=0.1)
                last_push = current_time
            except: pass

        # 4. Drawing
        overlay = frame.copy()
        
        # Parking Spots
        for i, spot in enumerate(spots_json):
            pts = (np.array(spot["points"], dtype=np.float32) * [scale_x, scale_y]).astype(np.int32)
            is_occupied = i in occupied_indices
            color = (0, 0, 255) if is_occupied else (0, 255, 0)
            cv2.polylines(frame, [pts], True, color, 2)
            cv2.fillPoly(overlay, [pts], color)
            
            # Spot Label
            cx, cy = int(spot["center"][0] * scale_x), int(spot["center"][1] * scale_y)
            cv2.putText(frame, f"S{i+1}", (cx-10, cy+5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)

        # Active Trackers
        new_trackers = []
        for t in trackers:
            t.update()
            if t.active:
                x, y = int(t.x), int(t.y)
                # Trail
                for j in range(len(t.path)-1):
                    thickness = int(np.sqrt(10 / (j + 1)) * 2)
                    cv2.line(frame, t.path[j], t.path[j+1], (255, 255, 0), 1)
                
                # Bounding Box (Matches User Screenshot Style)
                cv2.rectangle(frame, (x-40, y-30), (x+40, y+30), (255, 100, 0), 2)
                # Label
                cv2.rectangle(frame, (x-40, y-50), (x+40, y-30), (255, 100, 0), -1)
                cv2.putText(frame, t.id, (x-35, y-35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
                # Analytical Marker
                cv2.drawMarker(frame, (x, y), (0, 255, 255), cv2.MARKER_CROSS, 20, 2)
                
                new_trackers.append(t)
        trackers = new_trackers

        # UI Headers
        cv2.rectangle(frame, (0, 0), (w, 100), (30, 30, 30), -1)
        cv2.putText(frame, "RUParked [ACTIVE TRACKING]", (25, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 3)
        
        # Stats
        total = len(spots_json)
        avail = total - len(occupied_indices)
        cv2.putText(frame, f"TOTAL: {total} | FREE: {avail} | BUSY: {len(occupied_indices)}", (25, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
        
        # Percentage
        percent = int((avail / total) * 100)
        cv2.putText(frame, f"{percent}% FREE", (w-250, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 0), 3)

        # Scanner line
        scan_y = int((current_time * 200) % h)
        cv2.line(frame, (0, scan_y), (w, scan_y), (0, 255, 255), 1)

        # Final Blend
        frame = cv2.addWeighted(overlay, 0.2, frame, 0.8, 0)
        cv2.imshow("RUParked AI Vision", frame)
        if cv2.waitKey(30) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
