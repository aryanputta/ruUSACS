import cv2
import json
import time
import requests
import numpy as np
from pathlib import Path

# Configuration
VISION_API_URL = "http://localhost:8000/api/lots/yellow-lot/status"
VIDEO_SOURCE = str(Path(__file__).parent / "demo_parking.mp4")
ZONES_FILE = Path(__file__).parent / "manual_parking_zones.json"


def main():
    print("🚀 Starting RuParked Live Vision Demo...")
    print(f"📡 API: {VISION_API_URL}")
    
    # Try to open video
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    if not cap.isOpened():
        print("❌ Error: Could not open video source.")
        return

    cv2.namedWindow("RuParked - Live AI Vision", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("RuParked - Live AI Vision", 1280, 720)

    # Colors
    GREEN = (0, 255, 0)
    RED = (0, 0, 255)
    BLUE = (255, 100, 0)
    WHITE = (255, 255, 255)

    last_api_update = 0
    parking_data = None

    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        # Sync with Backend every 2 seconds
        if time.time() - last_api_update > 2:
            try:
                response = requests.get(VISION_API_URL, timeout=1)
                if response.status_code == 200:
                    parking_data = response.json()
                    last_api_update = time.time()
            except:
                pass

        # Draw Overlays
        if parking_data and "spots" in parking_data:
            overlay = frame.copy()
            for spot in parking_data["spots"]:
                pts = np.array(spot["polygon"], dtype=np.int32)
                occupied = spot["occupied"]
                color = RED if occupied else GREEN
                
                # Draw spot polygon
                cv2.polylines(frame, [pts], True, color, 2)
                cv2.fillPoly(overlay, [pts], color)
                
                # Draw ID label
                cx, cy = spot.get("center", [0, 0])
                label = f"S{spot['id']}" if isinstance(spot['id'], int) else spot['id']
                cv2.putText(frame, label, (cx-10, cy+5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, WHITE, 1)

            # Blend overlay
            frame = cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)

            # Draw Stats Header
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 60), (0, 0, 0), -1)
            stats_text = f"RUParked AI Vision | TOTAL: {parking_data['total_spots']} | OPEN: {parking_data['available']} | OCCUPIED: {parking_data['occupied']}"
            cv2.putText(frame, stats_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, BLUE, 2)
            
            # Status badge
            status_color = GREEN if parking_data['available'] > 0 else RED
            status_text = "READY" if parking_data['available'] > 0 else "FULL"
            cv2.putText(frame, status_text, (frame.shape[1]-120, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)

        cv2.imshow("RuParked - Live AI Vision", frame)
        
        # Exit on 'q'
        if cv2.waitKey(20) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
