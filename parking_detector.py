import json
import sys
import time
import copy
from datetime import datetime
import cv2
import numpy as np
from ultralytics import YOLO
from sklearn.cluster import DBSCAN

# Configuration
YOUTUBE_URL = "https://www.youtube.com/watch?v=U7HRKjlXK-Y"
MODEL_PATH = "yolo26n.pt"
CALIBRATION_FRAMES = 120
ZONES_FILE = "manual_parking_zones.json"
UPDATE_INTERVAL = 60  # Run detection every 60 seconds
OCCUPANCY_OUTPUT_FILE = "occupancy_data.json"  # JSON output for API consumption

# Colors (BGR)
GREEN = (0, 255, 0)
RED = (0, 0, 255)
YELLOW = (0, 255, 255)
WHITE = (255, 255, 255)
BLUE = (255, 100, 0)
CYAN = (255, 255, 0)

# COCO class IDs
VEHICLE_CLASSES = [2, 5, 7]  # car, bus, truck


def resolve_stream_source(source):
    """Resolve YouTube URLs to a direct stream URL so ultralytics can read them."""
    if not source or not isinstance(source, str):
        return source
    s = source.strip().lower()
    if "youtube.com" in s or "youtu.be" in s:
        try:
            import yt_dlp
            opts = {"format": "best[ext=mp4]/best", "quiet": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(source, download=False)
                if info and info.get("url"):
                    return info["url"]
                # fallback: try requested_formats
                fmts = info.get("requested_formats") or []
                if fmts and fmts[0].get("url"):
                    return fmts[0]["url"]
        except Exception as e:
            print(f"yt-dlp failed to resolve YouTube URL: {e}")
            print("Install/update with: pip install -U yt-dlp")
        return source
    return source


# ==================== MANUAL DRAWING MODE ====================

class SpotDrawer:
    """Interactive parking spot drawer using mouse clicks."""

    def __init__(self, frame):
        self.original_frame = frame.copy()
        self.frame = frame.copy()
        self.spots = []
        self.current_polygon = []
        self.drawing = False
        self.done = False

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # Left click: add point to current polygon
            self.current_polygon.append([x, y])
            self.redraw()

        elif event == cv2.EVENT_RBUTTONDOWN:
            # Right click: finish current polygon (need at least 3 points)
            if len(self.current_polygon) >= 3:
                # Calculate center
                pts = np.array(self.current_polygon)
                center = pts.mean(axis=0).astype(int).tolist()

                self.spots.append({
                    "id": len(self.spots),
                    "points": self.current_polygon.copy(),
                    "center": center
                })
                print(f"  Spot #{len(self.spots)} created with {len(self.current_polygon)} points")
                self.current_polygon = []
                self.redraw()
            else:
                print("  Need at least 3 points for a polygon. Keep clicking.")

        elif event == cv2.EVENT_MBUTTONDOWN:
            # Middle click: undo last point
            if self.current_polygon:
                self.current_polygon.pop()
                self.redraw()

    def redraw(self):
        """Redraw frame with all spots and current polygon."""
        self.frame = self.original_frame.copy()

        # Draw completed spots
        for i, spot in enumerate(self.spots):
            pts = np.array(spot["points"], dtype=np.int32)
            cv2.polylines(self.frame, [pts], True, GREEN, 2)
            cv2.fillPoly(self.frame, [pts], (*GREEN[:3], 50))

            # Label
            cx, cy = spot["center"]
            cv2.putText(self.frame, f"#{i+1}", (cx-10, cy+5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 2)

        # Draw current polygon in progress
        if self.current_polygon:
            pts = np.array(self.current_polygon, dtype=np.int32)

            # Draw points
            for pt in self.current_polygon:
                cv2.circle(self.frame, tuple(pt), 5, CYAN, -1)

            # Draw lines between points
            if len(self.current_polygon) > 1:
                cv2.polylines(self.frame, [pts], False, CYAN, 2)

        # Draw instructions
        self.draw_instructions()

    def draw_instructions(self):
        """Draw instruction overlay."""
        h, w = self.frame.shape[:2]

        # Semi-transparent background
        overlay = self.frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 80), (0, 0, 0), -1)
        self.frame = cv2.addWeighted(overlay, 0.7, self.frame, 0.3, 0)

        # Instructions
        cv2.putText(self.frame, "MANUAL SPOT DRAWING MODE", (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, YELLOW, 2)
        cv2.putText(self.frame, "Left-click: Add point | Right-click: Finish polygon | "
                   "Middle-click: Undo point", (10, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, WHITE, 1)
        cv2.putText(self.frame, f"Press 'S' to save & start | 'R' to reset | 'Q' to quit | "
                   f"Spots: {len(self.spots)}", (10, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, WHITE, 1)

    def run(self):
        """Run the interactive drawing interface."""
        cv2.namedWindow("Draw Parking Spots")
        cv2.setMouseCallback("Draw Parking Spots", self.mouse_callback)

        self.redraw()

        print("\n" + "="*60)
        print("MANUAL SPOT DRAWING MODE")
        print("="*60)
        print("Instructions:")
        print("  - Left-click to add points for a polygon")
        print("  - Right-click to finish the current polygon")
        print("  - Middle-click to undo the last point")
        print("  - Press 'S' to save spots and start detection")
        print("  - Press 'R' to reset all spots")
        print("  - Press 'Q' to quit without saving")
        print("="*60 + "\n")

        while True:
            cv2.imshow("Draw Parking Spots", self.frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('s') or key == ord('S'):
                if len(self.spots) > 0:
                    print(f"\nSaving {len(self.spots)} spots...")
                    self.done = True
                    break
                else:
                    print("No spots drawn yet. Draw at least one spot.")

            elif key == ord('r') or key == ord('R'):
                print("Resetting all spots...")
                self.spots = []
                self.current_polygon = []
                self.redraw()

            elif key == ord('q') or key == ord('Q'):
                print("Quitting without saving...")
                self.spots = []
                break

            elif key == 27:  # ESC
                print("Cancelled.")
                self.spots = []
                break

        cv2.destroyWindow("Draw Parking Spots")
        return self.spots


def run_manual_drawing(source):
    """Extract a frame and run manual spot drawing."""
    source = resolve_stream_source(source)
    print(f"Loading video from: {source}")
    print("Extracting frame for drawing...")

    # Use YOLO to get a frame (handles YouTube URLs)
    model = YOLO(MODEL_PATH)
    results = model.predict(source=source, stream=True, show=False, verbose=False)

    # Get frame ~3 seconds in (skip first 90 frames at 30fps)
    frame = None
    for i, result in enumerate(results):
        if i == 90:  # ~3 seconds
            frame = result.orig_img.copy()
            break
        if i > 100:
            break

    if frame is None:
        # Fallback: use first available frame
        results = model.predict(source=source, stream=True, show=False, verbose=False)
        for result in results:
            frame = result.orig_img.copy()
            break

    if frame is None:
        print("Error: Could not extract frame from video")
        sys.exit(1)

    print(f"Frame extracted: {frame.shape[1]}x{frame.shape[0]}")

    # Run drawer
    drawer = SpotDrawer(frame)
    spots = drawer.run()

    if spots:
        # Save to file
        with open(ZONES_FILE, 'w') as f:
            json.dump(spots, f, indent=2)
        print(f"Saved {len(spots)} spots to {ZONES_FILE}")

    return spots


# ==================== AUTO DETECTION FUNCTIONS ====================

def detect_parking_lines(frame):
    """Detect white/yellow parking line markings."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    _, white_mask = cv2.threshold(enhanced, 200, 255, cv2.THRESH_BINARY)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    yellow_lower = np.array([15, 80, 80])
    yellow_upper = np.array([35, 255, 255])
    yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)

    line_mask = cv2.bitwise_or(white_mask, yellow_mask)
    kernel = np.ones((3, 3), np.uint8)
    line_mask = cv2.morphologyEx(line_mask, cv2.MORPH_CLOSE, kernel)
    line_mask = cv2.morphologyEx(line_mask, cv2.MORPH_OPEN, kernel)

    edges = cv2.Canny(line_mask, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 30, minLineLength=20, maxLineGap=15)

    if lines is None:
        return []

    return [{'start': (l[0][0], l[0][1]), 'end': (l[0][2], l[0][3]),
             'midpoint': ((l[0][0]+l[0][2])//2, (l[0][1]+l[0][3])//2)}
            for l in lines]


def create_spot_from_vehicle(bbox, padding=0.15):
    """Create spot from vehicle bounding box."""
    x1, y1, x2, y2 = bbox
    w, h = x2 - x1, y2 - y1
    pw, ph = w * padding, h * padding

    sx1, sy1 = int(x1 - pw), int(y1 - ph)
    sx2, sy2 = int(x2 + pw), int(y2 + ph)

    return {
        "points": [[sx1, sy1], [sx2, sy1], [sx2, sy2], [sx1, sy2]],
        "center": [(sx1 + sx2) // 2, (sy1 + sy2) // 2],
        "width": sx2 - sx1, "height": sy2 - sy1
    }


def find_empty_spots(occupied_spots, frame_shape):
    """Find empty spots by analyzing gaps."""
    if len(occupied_spots) < 2:
        return []

    h, w = frame_shape[:2]
    empty = []

    # Group by row
    rows = {}
    for spot in occupied_spots:
        row_y = spot["center"][1] // 50 * 50
        rows.setdefault(row_y, []).append(spot)

    for row_y, row_spots in rows.items():
        row_spots = sorted(row_spots, key=lambda s: s["center"][0])
        if len(row_spots) < 2:
            continue

        avg_w = np.mean([s["width"] for s in row_spots])
        avg_h = np.mean([s["height"] for s in row_spots])

        spacings = [row_spots[i+1]["center"][0] - row_spots[i]["center"][0]
                   for i in range(len(row_spots)-1)]
        avg_spacing = np.median(spacings) if spacings else avg_w * 1.1

        # Find gaps
        for i in range(len(row_spots) - 1):
            gap = row_spots[i+1]["center"][0] - row_spots[i]["center"][0]
            if gap > avg_spacing * 1.5:
                num_empty = int(round(gap / avg_spacing)) - 1
                for j in range(1, num_empty + 1):
                    ratio = j / (num_empty + 1)
                    ex = int(row_spots[i]["center"][0] + gap * ratio)
                    ey = int(row_spots[i]["center"][1])

                    empty.append({
                        "points": [[ex-int(avg_w)//2, ey-int(avg_h)//2],
                                  [ex+int(avg_w)//2, ey-int(avg_h)//2],
                                  [ex+int(avg_w)//2, ey+int(avg_h)//2],
                                  [ex-int(avg_w)//2, ey+int(avg_h)//2]],
                        "center": [ex, ey], "width": int(avg_w), "height": int(avg_h),
                        "inferred": True
                    })

    return empty


def merge_spots(spots, min_dist=40):
    """Merge overlapping spots."""
    if len(spots) <= 1:
        return spots

    spots = sorted(spots, key=lambda s: s.get("inferred", False))
    merged = []

    for spot in spots:
        c1 = spot["center"]
        dup = False
        for existing in merged:
            c2 = existing["center"]
            if np.sqrt((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2) < min_dist:
                dup = True
                break
        if not dup:
            merged.append(spot)

    for i, s in enumerate(merged):
        s["id"] = i

    return merged


def scale_spots(spots, original_size, target_size):
    """Scale spot coordinates from original resolution to target resolution."""
    if original_size == target_size:
        return spots
    
    scale_x = target_size[0] / original_size[0]
    scale_y = target_size[1] / original_size[1]
    
    scaled_spots = []
    for spot in spots:
        scaled_spot = {
            "id": spot.get("id", len(scaled_spots)),
            "points": [[int(p[0] * scale_x), int(p[1] * scale_y)] for p in spot["points"]],
            "center": [int(spot["center"][0] * scale_x), int(spot["center"][1] * scale_y)]
        }
        scaled_spots.append(scaled_spot)
    
    return scaled_spots


def detect_spot_resolution(spots):
    """Detect the resolution the spots were drawn at based on max coordinates."""
    max_x = 0
    max_y = 0
    for spot in spots:
        for p in spot["points"]:
            max_x = max(max_x, p[0])
            max_y = max(max_y, p[1])
    
    # Common resolutions to check against
    resolutions = [
        (1920, 1080),
        (1280, 720),
        (854, 480),
        (640, 360),
    ]
    
    # Find the smallest resolution that fits all points
    for w, h in resolutions:
        if max_x <= w and max_y <= h:
            return (w, h)
    
    # If no match, return padded estimate
    return (int(max_x * 1.1), int(max_y * 1.1))


def compute_iou(box1, polygon_points):
    """Compute IoU between a bounding box and a polygon."""
    x1, y1, x2, y2 = box1
    
    # Create box polygon
    box_poly = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32)
    spot_poly = np.array(polygon_points, dtype=np.float32)
    
    # Use cv2 to compute intersection
    try:
        ret, intersection = cv2.intersectConvexConvex(box_poly, spot_poly)
        if ret <= 0 or intersection is None or len(intersection) < 3:
            return 0.0
        
        intersection_area = cv2.contourArea(intersection)
        box_area = (x2 - x1) * (y2 - y1)
        spot_area = cv2.contourArea(spot_poly)
        
        if box_area + spot_area - intersection_area <= 0:
            return 0.0
        
        iou = intersection_area / min(box_area, spot_area)  # Use min for better matching
        return iou
    except:
        return 0.0


def check_occupancy(spots, vehicles, iou_threshold=0.15):
    """Check spot occupancy using IoU (intersection over union) for robust matching."""
    occ = [False] * len(spots)
    
    if not spots or not vehicles:
        return occ

    for vx1, vy1, vx2, vy2 in vehicles:
        best_spot_idx = -1
        best_iou = 0.0

        for idx, spot in enumerate(spots):
            sp = spot["points"]
            
            # Compute IoU between vehicle box and spot polygon
            iou = compute_iou((vx1, vy1, vx2, vy2), sp)
            
            if iou > best_iou and iou >= iou_threshold:
                best_iou = iou
                best_spot_idx = idx
        
        # Also try point-in-polygon as fallback
        if best_spot_idx < 0:
            v_center_x = (vx1 + vx2) / 2
            v_center_y = (vy1 + vy2) / 2
            v_bottom_y = vy2
            
            for idx, spot in enumerate(spots):
                polygon = np.array(spot["points"], dtype=np.int32)
                
                # Check center or bottom-center
                center_inside = cv2.pointPolygonTest(polygon, (v_center_x, v_center_y), False) >= 0
                bottom_inside = cv2.pointPolygonTest(polygon, (v_center_x, v_bottom_y), False) >= 0
                
                if center_inside or bottom_inside:
                    best_spot_idx = idx
                    break

        if best_spot_idx >= 0:
            occ[best_spot_idx] = True

    return occ


def write_occupancy_json(spots, occupancy, output_path=OCCUPANCY_OUTPUT_FILE):
    """Write current occupancy state to JSON for API consumption.
    
    This function generates a JSON file that the FastAPI backend serves
    to the React frontend. The format matches what ruparked.jsx expects.
    """
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
            "label": f"S{idx + 1}",  # Human-readable label for frontend
            "occupied": is_occupied,
            "polygon": spot["points"],
            "center": spot.get("center", [0, 0])
        }
        data["spots"].append(spot_data)

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    return data


def draw_spots(frame, spots, occupancy):
    """Draw parking spots with clear labels."""
    overlay = frame.copy()
    h, w = frame.shape[:2]

    for idx, spot in enumerate(spots):
        pts = np.array(spot["points"], dtype=np.int32)
        is_occupied = occupancy[idx] if idx < len(occupancy) else False
        color = RED if is_occupied else GREEN

        # Fill polygon
        cv2.fillPoly(overlay, [pts], color)
        # Draw outline
        cv2.polylines(frame, [pts], True, color, 2)

        # Draw label at center
        cx, cy = spot.get("center", [0, 0])
        if cx == 0 and cy == 0:
            cx = int(np.mean([p[0] for p in spot["points"]]))
            cy = int(np.mean([p[1] for p in spot["points"]]))
        
        # Make sure label is visible on screen
        cx = max(20, min(w - 40, cx))
        cy = max(20, min(h - 20, cy))
        
        status = "X" if is_occupied else "O"
        label = f"{idx+1}"
        
        # Draw label background
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)
        cv2.rectangle(frame, (cx-tw//2-3, cy-th//2-3), (cx+tw//2+3, cy+th//2+3), (0,0,0), -1)
        cv2.putText(frame, label, (cx-tw//2, cy+th//2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, WHITE, 1)

    # Blend overlay
    result = cv2.addWeighted(overlay, 0.35, frame, 0.65, 0)
    return result


def draw_status(frame, total, available, occupied, calibrating=False, progress=0, mode="AUTO"):
    """Draw status bar."""
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 60), (30, 30, 30), -1)

    if calibrating:
        cv2.putText(frame, f"MAPPING LOT... {progress}/{CALIBRATION_FRAMES}", (10, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, YELLOW, 2)
        pct = progress / CALIBRATION_FRAMES
        cv2.rectangle(frame, (20, 50), (w-20, 58), (60,60,60), -1)
        cv2.rectangle(frame, (20, 50), (20+int((w-40)*pct), 58), YELLOW, -1)
    else:
        mode_color = CYAN if mode == "MANUAL" else WHITE
        cv2.putText(frame, f"RUParked [{mode}]", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, mode_color, 2)
        cv2.putText(frame, f"TOTAL: {total}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 1)
        cv2.putText(frame, f"AVAILABLE: {available}", (130, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, GREEN, 2)
        cv2.putText(frame, f"OCCUPIED: {occupied}", (300, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, RED, 2)

        pct = (available / total * 100) if total > 0 else 0
        color = GREEN if pct > 30 else YELLOW if pct > 10 else RED
        cv2.putText(frame, f"{pct:.0f}% FREE", (w-120, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    return frame


# ==================== MAIN ====================

def draw_vehicle_boxes(frame, vehicles, spots=None, color=BLUE):
    """Draw bounding boxes around detected vehicles with spot matching info."""
    for i, (x1, y1, x2, y2) in enumerate(vehicles):
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        
        # Check if vehicle matches any spot
        matched_spot = None
        if spots:
            v_center_x = (x1 + x2) / 2
            v_center_y = (y1 + y2) / 2
            for idx, spot in enumerate(spots):
                polygon = np.array(spot["points"], dtype=np.int32)
                if cv2.pointPolygonTest(polygon, (v_center_x, v_center_y), False) >= 0:
                    matched_spot = idx + 1
                    break
                # Also check bottom center
                if cv2.pointPolygonTest(polygon, (v_center_x, y2), False) >= 0:
                    matched_spot = idx + 1
                    break
        
        # Color: green if matched, blue if not
        box_color = GREEN if matched_spot else color
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
        
        # Label
        if matched_spot:
            label = f"CAR->S{matched_spot}"
        else:
            label = f"CAR"
        
        label_width = len(label) * 8 + 4
        cv2.rectangle(frame, (x1, y1 - 18), (x1 + label_width, y1), box_color, -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, WHITE, 1)
        
        # Draw center point for debugging
        cv2.circle(frame, (int((x1+x2)/2), int((y1+y2)/2)), 3, YELLOW, -1)
        cv2.circle(frame, (int((x1+x2)/2), y2), 3, CYAN, -1)  # Bottom center
        
    return frame


def post_to_backend(occupancy_data):
    """Post occupancy data to the backend API."""
    import requests
    try:
        response = requests.post(
            "http://localhost:8000/api/update-occupancy",
            json=occupancy_data,
            timeout=5
        )
        if response.status_code == 200:
            print(f"  -> Backend updated successfully")
        else:
            print(f"  -> Backend update failed: {response.status_code}")
    except requests.exceptions.ConnectionError:
        pass  # Backend not running, silently ignore
    except Exception as e:
        print(f"  -> Backend error: {e}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="RUParked - Parking Detection System")
    parser.add_argument("--manual", "-m", action="store_true",
                       help="Enable manual spot drawing mode")
    parser.add_argument("--source", "-s", default=YOUTUBE_URL,
                       help=f"Video source (default: {YOUTUBE_URL})")
    parser.add_argument("--load", "-l", type=str,
                       help="Load spots from JSON file instead of detecting")
    parser.add_argument("--interval", "-i", type=int, default=5,
                       help="Update interval in seconds (default: 5)")
    parser.add_argument("--conf", "-c", type=float, default=0.25,
                       help="Detection confidence threshold (default: 0.25)")
    parser.add_argument("--debug", "-d", action="store_true",
                       help="Enable debug output")
    args = parser.parse_args()

    update_interval = args.interval
    conf_threshold = args.conf
    debug_mode = args.debug

    source_display = args.source
    source = resolve_stream_source(args.source)
    parking_spots = []
    mode = "AUTO"

    print(f"Loading model: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)
    
    vehicle_class_names = [model.names.get(c, f"unknown_{c}") for c in VEHICLE_CLASSES]
    print(f"Detecting vehicle classes {VEHICLE_CLASSES}: {vehicle_class_names}")
    print(f"Confidence threshold: {conf_threshold}")

    # Manual drawing mode
    if args.manual:
        mode = "MANUAL"
        parking_spots = run_manual_drawing(source)
        if not parking_spots:
            print("No spots drawn. Exiting.")
            return

    # Load from file
    elif args.load:
        mode = "LOADED"
        print(f"Loading spots from {args.load}")
        try:
            with open(args.load, 'r') as f:
                parking_spots = json.load(f)
            print(f"Loaded {len(parking_spots)} parking spots")
            if len(parking_spots) == 0:
                print("WARNING: JSON file is empty! No spots to detect.")
            else:
                # Detect original resolution
                original_res = detect_spot_resolution(parking_spots)
                print(f"Spots appear to be drawn at resolution: {original_res[0]}x{original_res[1]}")
        except FileNotFoundError:
            print(f"ERROR: File not found: {args.load}")
            return
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in {args.load}: {e}")
            return
    
    # Store original spots for scaling (deep copy needed for nested dicts)
    original_parking_spots = copy.deepcopy(parking_spots) if parking_spots else []
    spots_original_res = detect_spot_resolution(original_parking_spots) if original_parking_spots else None

    # Run detection
    print(f"\nStarting detection on: {source_display}")
    if len(parking_spots) > 0:
        print(f"Using {len(parking_spots)} pre-defined spots (mode: {mode})")
    else:
        print(f"Auto-detecting spots ({CALIBRATION_FRAMES} calibration frames)")
    print(f"Update interval: {update_interval} seconds")
    print("Controls: 'q' to quit, 'u' for manual update, 's' to save snapshot")
    print("="*60)

    # Use OpenCV VideoCapture for reliable video reading
    print(f"Opening video stream...")
    cap = cv2.VideoCapture(source)
    
    if not cap.isOpened():
        print(f"ERROR: Could not open video source: {source}")
        return
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30  # Default fallback
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"Video: {frame_width}x{frame_height} @ {fps:.1f} FPS, {total_frames} frames")
    
    # Scale parking spots to match video resolution
    if parking_spots and spots_original_res:
        video_res = (frame_width, frame_height)
        if spots_original_res != video_res:
            print(f"Scaling spots from {spots_original_res[0]}x{spots_original_res[1]} to {frame_width}x{frame_height}")
            parking_spots = scale_spots(original_parking_spots, spots_original_res, video_res)
            print(f"Scaled {len(parking_spots)} spots to video resolution")
            # Show first few spots for debugging
            if debug_mode:
                print("First 3 scaled spots:")
                for i, spot in enumerate(parking_spots[:3]):
                    print(f"  Spot {i+1}: center={spot['center']}, points={spot['points'][:2]}...")
        else:
            print(f"Spots already at correct resolution")
    
    # Calculate frame delay for real-time playback
    frame_delay = int(1000 / fps)  # milliseconds per frame
    
    frame_count = 0
    collected_spots = []
    all_lines = []
    calibration_done = len(parking_spots) > 0
    frame_shape = None

    # Periodic update tracking
    last_update_time = 0
    last_occupancy = [False] * len(parking_spots) if parking_spots else []
    last_vehicles = []
    last_available = 0
    last_occupied = 0

    # Create window
    cv2.namedWindow("RUParked", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("RUParked", min(1280, frame_width), min(720, frame_height))

    print(f"\nStarting main loop - calibration_done={calibration_done}, spots={len(parking_spots)}")

    while True:
        ret, frame = cap.read()
        if not ret:
            # Try to loop video for continuous monitoring
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret:
                print("End of video stream")
                break
        
        frame_count += 1
        current_time = time.time()

        if frame_shape is None:
            frame_shape = frame.shape
            print(f"Processing frames: {frame_shape[1]}x{frame_shape[0]}")

        # Run YOLO detection on this frame
        results = model.predict(frame, verbose=False, conf=conf_threshold)
        
        # Extract vehicle detections
        current_vehicles = []
        if len(results) > 0 and results[0].boxes is not None:
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                if cls_id in VEHICLE_CLASSES:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    current_vehicles.append((x1, y1, x2, y2))

        # During calibration, collect vehicle positions
        if not calibration_done:
            for v in current_vehicles:
                collected_spots.append(create_spot_from_vehicle(v))

            # Line detection during calibration
            if frame_count % 10 == 0:
                all_lines.extend(detect_parking_lines(frame))

            # End calibration
            if frame_count == CALIBRATION_FRAMES:
                print(f"\nCalibration: {len(collected_spots)} vehicle detections, {len(all_lines)} lines")

                occupied_spots = merge_spots(collected_spots, 50)
                empty = find_empty_spots(occupied_spots, frame_shape)
                parking_spots = merge_spots(occupied_spots + empty, 45)

                print(f"Mapped {len(parking_spots)} spots")

                with open("auto_parking_zones.json", "w") as f:
                    json.dump(parking_spots, f, indent=2)

                calibration_done = True
                last_occupancy = [False] * len(parking_spots)
                last_update_time = 0  # Force immediate update
                print("\n" + "="*60)
                print(f"Live monitoring started (updates every {update_interval}s)")
                print("="*60 + "\n")

            frame = draw_status(frame, 0, 0, 0, calibrating=True, progress=frame_count)
            # Draw detected vehicles during calibration
            frame = draw_vehicle_boxes(frame, current_vehicles, spots=None, color=YELLOW)

        # After calibration: run detection and update
        elif calibration_done:
            if not parking_spots:
                cv2.putText(frame, "NO PARKING SPOTS LOADED!", (50, 100),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.putText(frame, "Use --load <file.json> or --manual to define spots", (50, 140),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            else:
                # Check if it's time for a full update
                should_update = (current_time - last_update_time) >= update_interval or last_update_time == 0

                if should_update:
                    last_occupancy = check_occupancy(parking_spots, current_vehicles)
                    last_vehicles = current_vehicles
                    last_occupied = sum(last_occupancy)
                    last_available = len(parking_spots) - last_occupied
                    last_update_time = current_time

                    # Write JSON for frontend consumption
                    occupancy_data = write_occupancy_json(parking_spots, last_occupancy)

                    # Post to backend API
                    post_to_backend(occupancy_data)

                    print(f"[{time.strftime('%H:%M:%S')}] Update | Vehicles: {len(current_vehicles)} | "
                          f"Available: {last_available}/{len(parking_spots)} | Occupied: {last_occupied}")
                    
                    # Debug output
                    if debug_mode and current_vehicles:
                        print(f"  Vehicle boxes:")
                        for i, (vx1, vy1, vx2, vy2) in enumerate(current_vehicles):
                            print(f"    V{i+1}: ({int(vx1)},{int(vy1)}) -> ({int(vx2)},{int(vy2)}) center=({int((vx1+vx2)/2)},{int((vy1+vy2)/2)})")
                        occupied_spots = [i+1 for i, occ in enumerate(last_occupancy) if occ]
                        print(f"  Occupied spots: {occupied_spots if occupied_spots else 'None'}")

                # Always draw the current frame with spots and vehicles
                frame = draw_spots(frame, parking_spots, last_occupancy)
                frame = draw_vehicle_boxes(frame, current_vehicles, spots=parking_spots, color=BLUE)
                frame = draw_status(frame, len(parking_spots), last_available, last_occupied, mode=mode)

                # Show time until next update
                time_until_next = max(0, update_interval - (current_time - last_update_time))
                cv2.putText(frame, f"Next update: {int(time_until_next)}s", (frame.shape[1] - 180, frame.shape[0] - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 1)
                
                # Show vehicle count
                cv2.putText(frame, f"Vehicles detected: {len(current_vehicles)}", (10, frame.shape[0] - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, CYAN, 1)

        # Display the frame
        cv2.imshow("RUParked", frame)
        
        # Wait for key press - this controls playback speed
        key = cv2.waitKey(frame_delay) & 0xFF
        
        if key == ord('q'):
            print("Quit requested")
            break
        elif key == ord('u'):
            last_update_time = 0
            print("Manual update triggered...")
        elif key == ord('s'):
            # Save snapshot
            snapshot_name = f"snapshot_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(snapshot_name, frame)
            print(f"Saved snapshot: {snapshot_name}")

    cap.release()
    cv2.destroyAllWindows()
    
    print(f"\nDone. Total frames processed: {frame_count}")
    print(f"Total spots: {len(parking_spots)}")
    if not calibration_done:
        print(f"WARNING: Calibration never completed (needed {CALIBRATION_FRAMES} frames, got {frame_count})")
        print(f"Vehicle detections collected: {len(collected_spots)}")


if __name__ == "__main__":
    main()
