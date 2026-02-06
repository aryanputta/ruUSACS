import json
import sys
import cv2
import numpy as np
from ultralytics import YOLO
from sklearn.cluster import DBSCAN

# Configuration
YOUTUBE_URL = "https://www.youtube.com/watch?v=U7HRKjlXK-Y"
MODEL_PATH = "yolo26n.pt"
CALIBRATION_FRAMES = 120
ZONES_FILE = "manual_parking_zones.json"

# Colors (BGR)
GREEN = (0, 255, 0)
RED = (0, 0, 255)
YELLOW = (0, 255, 255)
WHITE = (255, 255, 255)
BLUE = (255, 100, 0)
CYAN = (255, 255, 0)

# COCO class IDs
VEHICLE_CLASSES = [2, 5, 7]  # car, bus, truck


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


def check_occupancy(spots, vehicles):
    """Check spot occupancy using IoU."""
    occ = [False] * len(spots)

    for vx1, vy1, vx2, vy2 in vehicles:
        v_area = (vx2-vx1) * (vy2-vy1)

        for idx, spot in enumerate(spots):
            if occ[idx]:
                continue

            sp = spot["points"]
            sx1, sy1 = sp[0]
            sx2, sy2 = sp[2]
            s_area = (sx2-sx1) * (sy2-sy1)

            ix1, iy1 = max(vx1, sx1), max(vy1, sy1)
            ix2, iy2 = min(vx2, sx2), min(vy2, sy2)

            if ix1 < ix2 and iy1 < iy2:
                inter = (ix2-ix1) * (iy2-iy1)
                if inter > 0.25 * s_area or inter > 0.25 * v_area:
                    occ[idx] = True

    return occ


def draw_spots(frame, spots, occupancy):
    """Draw parking spots."""
    overlay = frame.copy()

    for idx, spot in enumerate(spots):
        pts = np.array(spot["points"], dtype=np.int32)
        color = RED if occupancy[idx] else GREEN

        cv2.fillPoly(overlay, [pts], color)
        cv2.polylines(frame, [pts], True, color, 2)

        cx, cy = spot["center"]
        label = f"#{idx+1}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        cv2.rectangle(frame, (cx-tw//2-2, cy-th//2-2), (cx+tw//2+2, cy+th//2+2), (0,0,0), -1)
        cv2.putText(frame, label, (cx-tw//2, cy+th//2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, WHITE, 1)

    return cv2.addWeighted(overlay, 0.35, frame, 0.65, 0)


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

def main():
    import argparse

    parser = argparse.ArgumentParser(description="RUParked - Parking Detection System")
    parser.add_argument("--manual", "-m", action="store_true",
                       help="Enable manual spot drawing mode")
    parser.add_argument("--source", "-s", default=YOUTUBE_URL,
                       help=f"Video source (default: {YOUTUBE_URL})")
    parser.add_argument("--load", "-l", type=str,
                       help="Load spots from JSON file instead of detecting")
    args = parser.parse_args()

    source = args.source
    parking_spots = []
    mode = "AUTO"

    print(f"Loading model: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)

    # Manual drawing mode
    if args.manual:
        mode = "MANUAL"
        parking_spots = run_manual_drawing(source)
        if not parking_spots:
            print("No spots drawn. Exiting.")
            return

    # Load from file
    elif args.load:
        mode = "MANUAL"
        print(f"Loading spots from {args.load}")
        with open(args.load, 'r') as f:
            parking_spots = json.load(f)
        print(f"Loaded {len(parking_spots)} spots")

    # Run detection
    print(f"\nStarting detection on: {source}")
    if mode == "MANUAL":
        print(f"Using {len(parking_spots)} manually defined spots")
    else:
        print(f"Auto-detecting spots ({CALIBRATION_FRAMES} calibration frames)")
    print("="*60)

    results = model.predict(source=source, stream=True, show=False, verbose=False)

    frame_count = 0
    collected_spots = []
    all_lines = []
    calibration_done = mode == "MANUAL"  # Skip calibration if manual
    frame_shape = None

    for result in results:
        frame_count += 1
        frame = result.plot()

        if frame_shape is None:
            frame_shape = frame.shape

        # Get vehicles
        current_vehicles = []
        for box in result.boxes:
            if int(box.cls[0]) in VEHICLE_CLASSES:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                current_vehicles.append((x1, y1, x2, y2))

                if not calibration_done:
                    collected_spots.append(create_spot_from_vehicle((x1, y1, x2, y2)))

        # Line detection during calibration
        if not calibration_done and frame_count % 10 == 0:
            all_lines.extend(detect_parking_lines(frame))

        # End calibration
        if frame_count == CALIBRATION_FRAMES and not calibration_done:
            print(f"\nCalibration: {len(collected_spots)} detections, {len(all_lines)} lines")

            occupied = merge_spots(collected_spots, 50)
            empty = find_empty_spots(occupied, frame_shape)
            parking_spots = merge_spots(occupied + empty, 45)

            print(f"Mapped {len(parking_spots)} spots")

            with open("auto_parking_zones.json", "w") as f:
                json.dump(parking_spots, f, indent=2)

            calibration_done = True
            print("\n" + "="*60)
            print("Live monitoring started")
            print("="*60 + "\n")

        # Draw
        if not calibration_done:
            frame = draw_status(frame, 0, 0, 0, calibrating=True, progress=frame_count)
        elif parking_spots:
            occ = check_occupancy(parking_spots, current_vehicles)
            occupied = sum(occ)
            available = len(parking_spots) - occupied

            frame = draw_spots(frame, parking_spots, occ)
            frame = draw_status(frame, len(parking_spots), available, occupied, mode=mode)

            if frame_count % 30 == 0:
                print(f"Frame {frame_count} | Available: {available}/{len(parking_spots)} | Occupied: {occupied}")

        cv2.imshow("RUParked", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()
    print(f"\nDone. Total spots: {len(parking_spots)}")


if __name__ == "__main__":
    main()
