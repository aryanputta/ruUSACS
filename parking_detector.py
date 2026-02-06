import json
import cv2
import numpy as np
from ultralytics import YOLO
from sklearn.cluster import DBSCAN

# Configuration
YOUTUBE_URL = "https://www.youtube.com/watch?v=U7HRKjlXK-Y"
MODEL_PATH = "yolo26n.pt"
CALIBRATION_FRAMES = 120

# Colors (BGR)
GREEN = (0, 255, 0)
RED = (0, 0, 255)
YELLOW = (0, 255, 255)
WHITE = (255, 255, 255)
BLUE = (255, 100, 0)

# COCO class IDs
VEHICLE_CLASSES = [2, 5, 7]  # car, bus, truck

print(f"Loading model: {MODEL_PATH}")
model = YOLO(MODEL_PATH)


def detect_parking_lines(frame):
    """
    Detect white/yellow parking line markings using edge detection.
    Returns line segments that likely represent parking boundaries.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Enhance contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Threshold to find white lines (parking markings are usually white/yellow)
    _, white_mask = cv2.threshold(enhanced, 200, 255, cv2.THRESH_BINARY)

    # Also detect using HSV for yellow lines
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    yellow_lower = np.array([15, 80, 80])
    yellow_upper = np.array([35, 255, 255])
    yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)

    # Combine masks
    line_mask = cv2.bitwise_or(white_mask, yellow_mask)

    # Morphological operations to clean up
    kernel = np.ones((3, 3), np.uint8)
    line_mask = cv2.morphologyEx(line_mask, cv2.MORPH_CLOSE, kernel)
    line_mask = cv2.morphologyEx(line_mask, cv2.MORPH_OPEN, kernel)

    # Edge detection
    edges = cv2.Canny(line_mask, 50, 150)

    # Detect lines using Hough Transform
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi/180,
        threshold=30,
        minLineLength=20,
        maxLineGap=15
    )

    if lines is None:
        return [], line_mask

    detected_lines = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
        angle = np.abs(np.arctan2(y2-y1, x2-x1) * 180 / np.pi)

        # Filter: keep lines that are somewhat vertical or horizontal
        # (parking lines are usually perpendicular or parallel to driving lanes)
        if length > 15:
            detected_lines.append({
                'start': (x1, y1),
                'end': (x2, y2),
                'length': length,
                'angle': angle,
                'midpoint': ((x1+x2)//2, (y1+y2)//2)
            })

    return detected_lines, line_mask


def create_spot_from_vehicle(vehicle_bbox, padding_ratio=0.15):
    """
    Create a parking spot sized to fit the detected vehicle.
    Uses the car's bounding box as context for spot size.
    Adds padding around the vehicle to create the spot boundary.
    """
    x1, y1, x2, y2 = vehicle_bbox
    width = x2 - x1
    height = y2 - y1

    # Add padding (spots are slightly larger than cars)
    pad_w = width * padding_ratio
    pad_h = height * padding_ratio

    spot_x1 = int(x1 - pad_w)
    spot_y1 = int(y1 - pad_h)
    spot_x2 = int(x2 + pad_w)
    spot_y2 = int(y2 + pad_h)

    center_x = (spot_x1 + spot_x2) // 2
    center_y = (spot_y1 + spot_y2) // 2

    return {
        "points": [[spot_x1, spot_y1], [spot_x2, spot_y1], [spot_x2, spot_y2], [spot_x1, spot_y2]],
        "center": [center_x, center_y],
        "width": spot_x2 - spot_x1,
        "height": spot_y2 - spot_y1,
        "vehicle_width": width,
        "vehicle_height": height
    }


def find_empty_spots_from_lines(lines, occupied_spots, frame_shape):
    """
    Use detected parking lines to find potential empty spots.
    Looks for gaps between lines that match typical spot dimensions.
    """
    if len(lines) < 2 or len(occupied_spots) == 0:
        return []

    h, w = frame_shape[:2]
    empty_spots = []

    # Get average spot dimensions from occupied spots (perspective-aware)
    # Group spots by Y position (row) to handle perspective
    spots_by_row = {}
    for spot in occupied_spots:
        row_y = spot["center"][1] // 50 * 50  # Group by 50px bands
        if row_y not in spots_by_row:
            spots_by_row[row_y] = []
        spots_by_row[row_y].append(spot)

    # For each row, find gaps that could be empty spots
    for row_y, row_spots in spots_by_row.items():
        if len(row_spots) == 0:
            continue

        # Sort spots by X position
        row_spots = sorted(row_spots, key=lambda s: s["center"][0])

        # Get average dimensions for this row (handles perspective)
        avg_width = np.mean([s["width"] for s in row_spots])
        avg_height = np.mean([s["height"] for s in row_spots])

        # Calculate typical spacing
        if len(row_spots) > 1:
            spacings = []
            for i in range(len(row_spots) - 1):
                gap = row_spots[i+1]["center"][0] - row_spots[i]["center"][0]
                spacings.append(gap)
            avg_spacing = np.median(spacings)
        else:
            avg_spacing = avg_width * 1.1

        # Look for gaps between adjacent spots
        for i in range(len(row_spots) - 1):
            spot1 = row_spots[i]
            spot2 = row_spots[i + 1]

            gap = spot2["center"][0] - spot1["center"][0]

            # If gap is larger than 1.5x normal spacing, there might be empty spots
            if gap > avg_spacing * 1.5:
                num_empty = int(round(gap / avg_spacing)) - 1

                for j in range(1, num_empty + 1):
                    # Interpolate position
                    ratio = j / (num_empty + 1)
                    empty_x = int(spot1["center"][0] + gap * ratio)
                    empty_y = int(spot1["center"][1] + (spot2["center"][1] - spot1["center"][1]) * ratio)

                    # Interpolate size (for perspective)
                    empty_w = int(spot1["width"] + (spot2["width"] - spot1["width"]) * ratio)
                    empty_h = int(spot1["height"] + (spot2["height"] - spot1["height"]) * ratio)

                    x1 = empty_x - empty_w // 2
                    y1 = empty_y - empty_h // 2
                    x2 = empty_x + empty_w // 2
                    y2 = empty_y + empty_h // 2

                    empty_spots.append({
                        "points": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
                        "center": [empty_x, empty_y],
                        "width": empty_w,
                        "height": empty_h,
                        "inferred": True
                    })

        # Extend row on left side
        first_spot = row_spots[0]
        if first_spot["center"][0] > avg_spacing * 1.5:
            # Room for spots on the left
            num_left = min(3, int(first_spot["center"][0] / avg_spacing))
            for j in range(1, num_left + 1):
                empty_x = int(first_spot["center"][0] - avg_spacing * j)
                if empty_x < avg_width // 2:
                    break
                empty_y = first_spot["center"][1]

                x1 = empty_x - int(avg_width) // 2
                y1 = empty_y - int(avg_height) // 2
                x2 = empty_x + int(avg_width) // 2
                y2 = empty_y + int(avg_height) // 2

                if x1 > 0:
                    empty_spots.append({
                        "points": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
                        "center": [empty_x, empty_y],
                        "width": int(avg_width),
                        "height": int(avg_height),
                        "inferred": True
                    })

        # Extend row on right side
        last_spot = row_spots[-1]
        if last_spot["center"][0] < w - avg_spacing * 1.5:
            num_right = min(3, int((w - last_spot["center"][0]) / avg_spacing))
            for j in range(1, num_right + 1):
                empty_x = int(last_spot["center"][0] + avg_spacing * j)
                if empty_x > w - avg_width // 2:
                    break
                empty_y = last_spot["center"][1]

                x1 = empty_x - int(avg_width) // 2
                y1 = empty_y - int(avg_height) // 2
                x2 = empty_x + int(avg_width) // 2
                y2 = empty_y + int(avg_height) // 2

                if x2 < w:
                    empty_spots.append({
                        "points": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
                        "center": [empty_x, empty_y],
                        "width": int(avg_width),
                        "height": int(avg_height),
                        "inferred": True
                    })

    return empty_spots


def merge_spots(spots, min_distance=40):
    """Remove overlapping spots, keeping the better defined ones."""
    if len(spots) <= 1:
        return spots

    # Sort by whether they're inferred (real spots first)
    spots = sorted(spots, key=lambda s: s.get("inferred", False))

    merged = []
    for spot in spots:
        c1 = spot["center"]
        is_duplicate = False

        for existing in merged:
            c2 = existing["center"]
            dist = np.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)
            if dist < min_distance:
                is_duplicate = True
                break

        if not is_duplicate:
            merged.append(spot)

    # Assign IDs
    for i, spot in enumerate(merged):
        spot["id"] = i

    return merged


def check_occupancy(spots, vehicle_boxes):
    """Check which spots are occupied using IoU overlap."""
    occupancy = [False] * len(spots)

    for vbox in vehicle_boxes:
        vx1, vy1, vx2, vy2 = vbox
        v_area = (vx2 - vx1) * (vy2 - vy1)

        for idx, spot in enumerate(spots):
            if occupancy[idx]:
                continue

            sp = spot["points"]
            sx1, sy1 = sp[0]
            sx2, sy2 = sp[2]
            s_area = (sx2 - sx1) * (sy2 - sy1)

            # Calculate intersection
            ix1 = max(vx1, sx1)
            iy1 = max(vy1, sy1)
            ix2 = min(vx2, sx2)
            iy2 = min(vy2, sy2)

            if ix1 < ix2 and iy1 < iy2:
                intersection = (ix2 - ix1) * (iy2 - iy1)
                # Occupied if >25% overlap with spot or vehicle
                if intersection > 0.25 * s_area or intersection > 0.25 * v_area:
                    occupancy[idx] = True

    return occupancy


def draw_spots(frame, spots, occupancy):
    """Draw parking spots with colors."""
    overlay = frame.copy()

    for idx, spot in enumerate(spots):
        pts = np.array(spot["points"], dtype=np.int32)
        color = RED if occupancy[idx] else GREEN

        # Fill
        cv2.fillPoly(overlay, [pts], color)
        # Border
        cv2.polylines(frame, [pts], True, color, 2)

        # Label
        cx, cy = spot["center"]
        label = f"#{idx+1}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        cv2.rectangle(frame, (cx-tw//2-2, cy-th//2-2), (cx+tw//2+2, cy+th//2+2), (0,0,0), -1)
        cv2.putText(frame, label, (cx-tw//2, cy+th//2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, WHITE, 1)

    return cv2.addWeighted(overlay, 0.35, frame, 0.65, 0)


def draw_lines_debug(frame, lines):
    """Draw detected parking lines for debugging."""
    for line in lines:
        cv2.line(frame, line['start'], line['end'], BLUE, 1)
    return frame


def draw_status(frame, total, available, occupied, calibrating=False, progress=0):
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
        cv2.putText(frame, "RUParked", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2)
        cv2.putText(frame, f"TOTAL: {total}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 1)
        cv2.putText(frame, f"AVAILABLE: {available}", (130, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, GREEN, 2)
        cv2.putText(frame, f"OCCUPIED: {occupied}", (300, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, RED, 2)

        pct = (available / total * 100) if total > 0 else 0
        color = GREEN if pct > 30 else YELLOW if pct > 10 else RED
        cv2.putText(frame, f"{pct:.0f}% FREE", (w-120, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    return frame


# === MAIN ===
print(f"\nStarting on: {YOUTUBE_URL}")
print(f"Phase 1: Mapping parking lot ({CALIBRATION_FRAMES} frames)")
print("="*60)

results = model.predict(source=YOUTUBE_URL, stream=True, show=False, verbose=False)

frame_count = 0
collected_spots = []  # Spots created from vehicle bounding boxes
all_lines = []
parking_spots = []
calibration_done = False
frame_shape = None

for result in results:
    frame_count += 1
    frame = result.plot()

    if frame_shape is None:
        frame_shape = frame.shape

    # Get current vehicles
    current_vehicles = []
    boxes = result.boxes
    for box in boxes:
        if int(box.cls[0]) in VEHICLE_CLASSES:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            current_vehicles.append((x1, y1, x2, y2))

            # During calibration, create spot from each vehicle's bounding box
            if not calibration_done:
                spot = create_spot_from_vehicle((x1, y1, x2, y2))
                collected_spots.append(spot)

    # Detect parking lines during calibration
    if not calibration_done and frame_count % 10 == 0:
        lines, _ = detect_parking_lines(frame)
        all_lines.extend(lines)

    # After calibration
    if frame_count == CALIBRATION_FRAMES and not calibration_done:
        print(f"\nCollected {len(collected_spots)} vehicle-based spots")
        print(f"Detected {len(all_lines)} line segments")

        # Merge collected spots (same car detected multiple times)
        occupied_spots = merge_spots(collected_spots, min_distance=50)
        print(f"Merged to {len(occupied_spots)} unique occupied spots")

        # Find empty spots based on gaps and lines
        empty_spots = find_empty_spots_from_lines(all_lines, occupied_spots, frame_shape)
        print(f"Inferred {len(empty_spots)} potential empty spots")

        # Combine all spots
        all_spots = occupied_spots + empty_spots
        parking_spots = merge_spots(all_spots, min_distance=45)

        print(f"Total mapped: {len(parking_spots)} parking spots")

        with open("auto_parking_zones.json", "w") as f:
            json.dump(parking_spots, f, indent=2)

        calibration_done = True
        print("\n" + "="*60)
        print("Phase 2: Live monitoring")
        print("="*60 + "\n")

    # Draw
    if not calibration_done:
        frame = draw_status(frame, 0, 0, 0, calibrating=True, progress=frame_count)
    elif len(parking_spots) > 0:
        occupancy = check_occupancy(parking_spots, current_vehicles)
        occupied = sum(occupancy)
        available = len(parking_spots) - occupied

        frame = draw_spots(frame, parking_spots, occupancy)
        frame = draw_status(frame, len(parking_spots), available, occupied)

        if frame_count % 30 == 0:
            print(f"Frame {frame_count} | Available: {available}/{len(parking_spots)} | Occupied: {occupied}")

    cv2.imshow("RUParked", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
print(f"\nDone. Mapped {len(parking_spots)} spots.")
