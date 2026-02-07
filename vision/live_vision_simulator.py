import cv2
import json
import time
import requests
import numpy as np
import os
from pathlib import Path

# Configuration
VISION_API_URL = "http://localhost:8000/api/lots/yellow-lot/status"
BACKGROUND_IMAGE = "/Users/srini/.gemini/antigravity/brain/903a54f8-7d21-4c32-83df-ff2c7002b0f4/parking_lot_camera_feed_1770437424276.png"

# Define representative spots based on the generated image
# These are manual polygons that fit the stalls in the prompt's image
MOCK_SPOTS = [
    {"id": "S1", "polygon": [[100, 300], [250, 280], [280, 420], [120, 450]]},
    {"id": "S2", "polygon": [[270, 275], [420, 255], [450, 390], [300, 415]]},
    {"id": "S3", "polygon": [[440, 250], [590, 230], [620, 360], [470, 385]]},
    {"id": "S4", "polygon": [[610, 225], [760, 205], [790, 335], [640, 355]]},
    {"id": "S5", "polygon": [[140, 470], [300, 450], [340, 600], [170, 630]]},
    {"id": "S6", "polygon": [[320, 445], [480, 425], [520, 570], [350, 600]]},
    {"id": "S7", "polygon": [[500, 420], [660, 400], [700, 540], [530, 570]]},
]

def main():
    print("🚀 Starting RuParked AI Vision Live Stream...")
    print(f"📡 API: {VISION_API_URL}")
    print(f"🖼️  Feed: {os.path.basename(BACKGROUND_IMAGE)}")
    
    # Load background
    base_frame = cv2.imread(BACKGROUND_IMAGE)
    if base_frame is None:
        print(f"❌ Error: Could not load background image at {BACKGROUND_IMAGE}")
        return

    # Create window
    cv2.namedWindow("RuParked - Live AI Camera Feed", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("RuParked - Live AI Camera Feed", 1000, 1000)

    # Colors
    GREEN = (0, 255, 0)
    RED = (0, 0, 255)
    BLUE = (255, 100, 0)
    WHITE = (255, 255, 255)
    CYAN = (255, 255, 0)

    last_api_update = 0
    parking_data = None

    while True:
        frame = base_frame.copy()
        
        # Sync with Backend every 1 second
        if time.time() - last_api_update > 1:
            try:
                response = requests.get(VISION_API_URL, timeout=0.5)
                if response.status_code == 200:
                    parking_data = response.json()
                    last_api_update = time.time()
            except:
                pass

        # Draw Overlays
        overlay = frame.copy()
        
        # We use the spots from the API if available, otherwise mock ones
        display_spots = parking_data["spots"] if parking_data and "spots" in parking_data else MOCK_SPOTS
        
        for i, spot in enumerate(display_spots):
            # If the API gave us spots, they might not match our background's perspective
            # So for the VISUAL demo, we map the API's 'occupied' status to our background's polygons
            mock_poly = MOCK_SPOTS[i % len(MOCK_SPOTS)]["polygon"]
            pts = np.array(mock_poly, dtype=np.int32)
            
            occupied = spot.get("occupied", False)
            color = RED if occupied else GREEN
            
            # Draw spot polygon
            cv2.polylines(frame, [pts], True, color, 3)
            cv2.fillPoly(overlay, [pts], color)
            
            # Label
            label = f"S{i+1}"
            center = np.mean(pts, axis=0).astype(int)
            cv2.putText(frame, label, (center[0]-20, center[1]+10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, WHITE, 2)

        # Blend overlay
        frame = cv2.addWeighted(overlay, 0.25, frame, 0.75, 0)

        # UI Chrome
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (0, 0), (w, 120), (0, 0, 0), -1)
        cv2.putText(frame, "RUParked AI VISION - LIVE CAM 04", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, CYAN, 3)
        
        if parking_data:
            stats = f"SPOTS: {parking_data['total_spots']} | FREE: {parking_data['available']} | OCCUPIED: {parking_data['occupied']}"
            cv2.putText(frame, stats, (30, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.9, WHITE, 2)
            
            # Timestamp
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, ts, (w-350, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, WHITE, 1)

        # Scanner line effect
        scan_y = int((time.time() * 200) % h)
        cv2.line(frame, (0, scan_y), (w, scan_y), (0, 255, 255), 1)

        cv2.imshow("RuParked - Live AI Camera Feed", frame)
        
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
