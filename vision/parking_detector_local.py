#!/usr/bin/env python3
"""
RUParked Local Video Detector
Simplified parking detection for local MP4 files.
"""

import json
import sys
import time
import argparse
from datetime import datetime
import cv2
import numpy as np
from ultralytics import YOLO

# Configuration
VIDEO_PATH = "parking_video.mp4"
MODEL_PATH = "yolo26n.pt"
ZONES_FILE = "manual_parking_zones.json"
UPDATE_INTERVAL = 5  # Run detection every 5 seconds
OCCUPANCY_OUTPUT_FILE = "occupancy_data.json"

# Colors (BGR)
GREEN = (0, 255, 0)
RED = (0, 0, 255)
YELLOW = (0, 255, 255)
WHITE = (255, 255, 255)
BLUE = (255, 100, 0)
CYAN = (255, 255, 0)

# COCO class IDs for vehicles
VEHICLE_CLASSES = [2, 5, 7]  # car, bus, truck


def load_parking_zones(zones_file):
    """Load parking zones from JSON file."""
    try:
        with open(zones_file, 'r') as f:
            spots = json.load(f)
        print(f"Loaded {len(spots)} parking spots from {zones_file}")
        return spots
    except FileNotFoundError:
        print(f"ERROR: Zones file not found: {zones_file}")
        return []
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {zones_file}: {e}")
        return []


def compute_iou(box1, polygon_points):
    """Compute IoU between a bounding box and a polygon."""
    x1, y1, x2, y2 = box1
    
    box_poly = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32)
    spot_poly = np.array(polygon_points, dtype=np.float32)
    
    try:
        ret, intersection = cv2.intersectConvexConvex(box_poly, spot_poly)
        if ret <= 0 or intersection is None or len(intersection) < 3:
            return 0.0
        
        intersection_area = cv2.contourArea(intersection)
        box_area = (x2 - x1) * (y2 - y1)
        spot_area = cv2.contourArea(spot_poly)
        
        if box_area + spot_area - intersection_area <= 0:
            return 0.0
        
        iou = intersection_area / min(box_area, spot_area)
        return iou
    except:
        return 0.0


def check_occupancy(spots, vehicles, iou_threshold=0.15):
    """Check spot occupancy using IoU for robust matching."""
    occ = [False] * len(spots)
    
    if not spots or not vehicles:
        return occ

    for vx1, vy1, vx2, vy2 in vehicles:
        best_spot_idx = -1
        best_iou = 0.0

        for idx, spot in enumerate(spots):
            sp = spot["points"]
            iou = compute_iou((vx1, vy1, vx2, vy2), sp)
            
            if iou > best_iou and iou >= iou_threshold:
                best_iou = iou
                best_spot_idx = idx
        
        # Fallback: point-in-polygon check
        if best_spot_idx < 0:
            v_center_x = (vx1 + vx2) / 2
            v_center_y = (vy1 + vy2) / 2
            v_bottom_y = vy2
            
            for idx, spot in enumerate(spots):
                polygon = np.array(spot["points"], dtype=np.int32)
                center_inside = cv2.pointPolygonTest(polygon, (v_center_x, v_center_y), False) >= 0
                bottom_inside = cv2.pointPolygonTest(polygon, (v_center_x, v_bottom_y), False) >= 0
                
                if center_inside or bottom_inside:
                    best_spot_idx = idx
                    break

        if best_spot_idx >= 0:
            occ[best_spot_idx] = True

    return occ


def write_occupancy_json(spots, occupancy, output_path=OCCUPANCY_OUTPUT_FILE):
    """Write current occupancy state to JSON."""
    data = {
        "timestamp": datetime.now().isoformat(),
        "lot_name": "Yellow Lot",
        "camera_section": "Yellow-NW",
        "total_spots": len(spots),
        "available": sum(1 for o in occupancy if not o),
        "occupied": sum(occupancy),
        "occupancy_rate": round(sum(occupancy) / len(spots) * 100, 1) if spots else 0,
        "spots": []
    }

    for idx, (spot, is_occupied) in enumerate(zip(spots, occupancy)):
        spot_data = {
            "id": spot.get("id", idx),
            "label": f"S{idx + 1}",
            "occupied": is_occupied,
            "polygon": spot["points"],
            "center": spot.get("center", [0, 0])
        }
        data["spots"].append(spot_data)

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    return data


def draw_spots(frame, spots, occupancy):
    """Draw parking spots with labels."""
    overlay = frame.copy()
    h, w = frame.shape[:2]

    for idx, spot in enumerate(spots):
        pts = np.array(spot["points"], dtype=np.int32)
        is_occupied = occupancy[idx] if idx < len(occupancy) else False
        color = RED if is_occupied else GREEN

        cv2.fillPoly(overlay, [pts], color)
        cv2.polylines(frame, [pts], True, color, 2)

        cx, cy = spot.get("center", [0, 0])
        if cx == 0 and cy == 0:
            cx = int(np.mean([p[0] for p in spot["points"]]))
            cy = int(np.mean([p[1] for p in spot["points"]]))
        
        cx = max(20, min(w - 40, cx))
        cy = max(20, min(h - 20, cy))
        
        label = f"{idx+1}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)
        cv2.rectangle(frame, (cx-tw//2-3, cy-th//2-3), (cx+tw//2+3, cy+th//2+3), (0,0,0), -1)
        cv2.putText(frame, label, (cx-tw//2, cy+th//2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, WHITE, 1)

    result = cv2.addWeighted(overlay, 0.35, frame, 0.65, 0)
    return result


def draw_vehicle_boxes(frame, vehicles, spots=None, color=BLUE):
    """Draw bounding boxes around detected vehicles."""
    for i, (x1, y1, x2, y2) in enumerate(vehicles):
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        
        matched_spot = None
        if spots:
            v_center_x = (x1 + x2) / 2
            v_center_y = (y1 + y2) / 2
            for idx, spot in enumerate(spots):
                polygon = np.array(spot["points"], dtype=np.int32)
                if cv2.pointPolygonTest(polygon, (v_center_x, v_center_y), False) >= 0:
                    matched_spot = idx + 1
                    break
                if cv2.pointPolygonTest(polygon, (v_center_x, y2), False) >= 0:
                    matched_spot = idx + 1
                    break
        
        box_color = GREEN if matched_spot else color
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
        
        label = f"CAR->S{matched_spot}" if matched_spot else "CAR"
        label_width = len(label) * 8 + 4
        cv2.rectangle(frame, (x1, y1 - 18), (x1 + label_width, y1), box_color, -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, WHITE, 1)
        
        cv2.circle(frame, (int((x1+x2)/2), int((y1+y2)/2)), 3, YELLOW, -1)
        cv2.circle(frame, (int((x1+x2)/2), y2), 3, CYAN, -1)
        
    return frame


def draw_status(frame, total, available, occupied):
    """Draw status bar."""
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 60), (30, 30, 30), -1)

    cv2.putText(frame, "RUParked [LOCAL]", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, CYAN, 2)
    cv2.putText(frame, f"TOTAL: {total}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 1)
    cv2.putText(frame, f"AVAILABLE: {available}", (130, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, GREEN, 2)
    cv2.putText(frame, f"OCCUPIED: {occupied}", (300, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, RED, 2)

    pct = (available / total * 100) if total > 0 else 0
    color = GREEN if pct > 30 else YELLOW if pct > 10 else RED
    cv2.putText(frame, f"{pct:.0f}% FREE", (w-120, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    return frame


def post_to_backend(occupancy_data):
    """Post occupancy data to the backend API."""
    try:
        import requests
        response = requests.post(
            "http://localhost:8000/api/update-occupancy",
            json=occupancy_data,
            timeout=5
        )
        if response.status_code == 200:
            print(f"  -> Backend updated successfully")
    except:
        pass  # Backend not running, silently ignore


def main():
    parser = argparse.ArgumentParser(description="RUParked Local Video Detector")
    parser.add_argument("--video", "-v", default=VIDEO_PATH,
                       help=f"Video file path (default: {VIDEO_PATH})")
    parser.add_argument("--zones", "-z", default=ZONES_FILE,
                       help=f"Parking zones JSON file (default: {ZONES_FILE})")
    parser.add_argument("--interval", "-i", type=int, default=UPDATE_INTERVAL,
                       help=f"Update interval in seconds (default: {UPDATE_INTERVAL})")
    parser.add_argument("--conf", "-c", type=float, default=0.15,
                       help="Detection confidence threshold (default: 0.15)")
    parser.add_argument("--imgsz", type=int, default=1280,
                       help="YOLO inference size - larger = better for small objects (default: 1280)")
    parser.add_argument("--loop", "-l", action="store_true",
                       help="Loop video continuously")
    parser.add_argument("--debug", "-d", action="store_true",
                       help="Enable debug output")
    args = parser.parse_args()

    # Load parking zones
    parking_spots = load_parking_zones(args.zones)
    if not parking_spots:
        print("No parking spots loaded. Exiting.")
        return

    # Load YOLO model
    print(f"Loading model: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)
    print(f"Detecting vehicle classes {VEHICLE_CLASSES}")
    print(f"Confidence threshold: {args.conf}")
    print(f"Inference size: {args.imgsz}px (larger = better for small objects)")

    # Open video file
    print(f"\nOpening video: {args.video}")
    cap = cv2.VideoCapture(args.video)
    
    if not cap.isOpened():
        print(f"ERROR: Could not open video: {args.video}")
        return
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = total_frames / fps if fps > 0 else 0
    
    print(f"Video: {frame_width}x{frame_height} @ {fps:.1f} FPS")
    print(f"Duration: {duration:.1f}s ({total_frames} frames)")
    print(f"Parking spots: {len(parking_spots)}")
    print(f"Update interval: {args.interval}s")
    print("\nControls: 'q' quit, 'u' manual update, 's' save snapshot, SPACE pause")
    print("="*60)

    frame_delay = int(1000 / fps)
    frame_count = 0
    paused = False
    
    # Tracking
    last_update_time = 0
    last_occupancy = [False] * len(parking_spots)
    last_available = len(parking_spots)
    last_occupied = 0

    # Create window
    cv2.namedWindow("RUParked Local", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("RUParked Local", min(1280, frame_width), min(720, frame_height))

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                if args.loop:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    print("\nEnd of video")
                    break
            
            frame_count += 1
        
        current_time = time.time()

        # Run YOLO detection with larger inference size for small objects
        results = model.predict(frame, verbose=False, conf=args.conf, imgsz=args.imgsz)
        
        # Extract vehicle detections
        current_vehicles = []
        if len(results) > 0 and results[0].boxes is not None:
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                if cls_id in VEHICLE_CLASSES:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    current_vehicles.append((x1, y1, x2, y2))

        # Check if time for update
        should_update = (current_time - last_update_time) >= args.interval or last_update_time == 0

        if should_update:
            last_occupancy = check_occupancy(parking_spots, current_vehicles)
            last_occupied = sum(last_occupancy)
            last_available = len(parking_spots) - last_occupied
            last_update_time = current_time

            # Write JSON for frontend
            occupancy_data = write_occupancy_json(parking_spots, last_occupancy)
            post_to_backend(occupancy_data)

            print(f"[{time.strftime('%H:%M:%S')}] Frame {frame_count}/{total_frames} | "
                  f"Vehicles: {len(current_vehicles)} | "
                  f"Available: {last_available}/{len(parking_spots)} | Occupied: {last_occupied}")
            
            if args.debug and current_vehicles:
                print(f"  Vehicle boxes:")
                for i, (vx1, vy1, vx2, vy2) in enumerate(current_vehicles):
                    print(f"    V{i+1}: ({int(vx1)},{int(vy1)}) -> ({int(vx2)},{int(vy2)})")

        # Draw visualization
        display_frame = frame.copy()
        display_frame = draw_spots(display_frame, parking_spots, last_occupancy)
        display_frame = draw_vehicle_boxes(display_frame, current_vehicles, spots=parking_spots)
        display_frame = draw_status(display_frame, len(parking_spots), last_available, last_occupied)

        # Show time until next update and frame info
        time_until_next = max(0, args.interval - (current_time - last_update_time))
        cv2.putText(display_frame, f"Next update: {int(time_until_next)}s", 
                   (frame_width - 180, frame_height - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 1)
        cv2.putText(display_frame, f"Vehicles: {len(current_vehicles)} | Frame: {frame_count}/{total_frames}", 
                   (10, frame_height - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, CYAN, 1)
        
        if paused:
            cv2.putText(display_frame, "PAUSED", (frame_width//2 - 50, frame_height//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, YELLOW, 2)

        cv2.imshow("RUParked Local", display_frame)
        
        key = cv2.waitKey(1 if paused else frame_delay) & 0xFF
        
        if key == ord('q'):
            print("Quit requested")
            break
        elif key == ord('u'):
            last_update_time = 0
            print("Manual update triggered...")
        elif key == ord('s'):
            snapshot_name = f"snapshot_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(snapshot_name, display_frame)
            print(f"Saved snapshot: {snapshot_name}")
        elif key == ord(' '):
            paused = not paused
            print("Paused" if paused else "Resumed")

    cap.release()
    cv2.destroyAllWindows()
    
    print(f"\nDone. Processed {frame_count} frames.")


if __name__ == "__main__":
    main()
