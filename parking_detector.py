import json
import cv2
import numpy as np
from ultralytics import YOLO
from sklearn.cluster import DBSCAN, KMeans

# Configuration
YOUTUBE_URL = "https://www.youtube.com/watch?v=U7HRKjlXK-Y"
MODEL_PATH = "yolo26n.pt"
CALIBRATION_FRAMES = 100  # Frames to analyze for spot detection

# Colors (BGR format for OpenCV)
GREEN = (0, 255, 0)      # Available
RED = (0, 0, 255)        # Occupied
YELLOW = (0, 255, 255)   # Calibrating
WHITE = (255, 255, 255)

# COCO class IDs for vehicles
VEHICLE_CLASSES = [2, 5, 7]  # car, bus, truck

# Load YOLO26 model
print(f"Loading model: {MODEL_PATH}")
model = YOLO(MODEL_PATH)


def detect_parking_lines(frame):
    """
    Detect parking line markings using edge detection and Hough Transform.
    Returns detected lines as list of ((x1,y1), (x2,y2)) tuples.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Edge detection
    edges = cv2.Canny(blurred, 50, 150)

    # Detect lines using Hough Transform
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi/180,
        threshold=50,
        minLineLength=30,
        maxLineGap=10
    )

    if lines is None:
        return []

    return [((line[0][0], line[0][1]), (line[0][2], line[0][3])) for line in lines]


def create_grid_from_vehicles(vehicle_positions, frame_shape):
    """
    Create a grid of parking spots by analyzing vehicle positions.
    Extrapolates to find ALL spots, not just occupied ones.
    """
    if len(vehicle_positions) < 3:
        return []

    h, w = frame_shape[:2]

    # Get average vehicle dimensions
    widths = [p[2] for p in vehicle_positions]
    heights = [p[3] for p in vehicle_positions]
    avg_width = np.median(widths)
    avg_height = np.median(heights)

    # Cluster vehicles into rows based on Y position
    y_positions = np.array([[p[1]] for p in vehicle_positions])

    # Determine number of rows using elbow method or fixed
    n_rows = min(5, max(1, len(vehicle_positions) // 3))

    if len(vehicle_positions) >= n_rows:
        kmeans_y = KMeans(n_clusters=n_rows, random_state=42, n_init=10)
        kmeans_y.fit(y_positions)
        row_centers = sorted(kmeans_y.cluster_centers_.flatten())
    else:
        row_centers = [np.mean(y_positions)]

    # For each row, find the x-range of vehicles
    parking_zones = []
    spot_id = 0

    for row_y in row_centers:
        # Find vehicles in this row (within avg_height distance)
        row_vehicles = [p for p in vehicle_positions if abs(p[1] - row_y) < avg_height]

        if len(row_vehicles) == 0:
            continue

        # Get x positions and find the range
        x_positions = sorted([p[0] for p in row_vehicles])

        # Calculate spacing between vehicles
        if len(x_positions) > 1:
            spacings = [x_positions[i+1] - x_positions[i] for i in range(len(x_positions)-1)]
            avg_spacing = np.median(spacings)
        else:
            avg_spacing = avg_width + 20  # Default gap

        # Determine row boundaries
        min_x = max(0, x_positions[0] - avg_spacing * 2)
        max_x = min(w, x_positions[-1] + avg_spacing * 2)

        # Create spots along this row
        current_x = min_x + avg_width / 2
        while current_x < max_x:
            x1 = int(current_x - avg_width/2 - 5)
            y1 = int(row_y - avg_height/2 - 5)
            x2 = int(current_x + avg_width/2 + 5)
            y2 = int(row_y + avg_height/2 + 5)

            # Ensure within frame bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            if x2 - x1 > 20 and y2 - y1 > 20:  # Minimum size check
                zone = {
                    "id": spot_id,
                    "points": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
                    "center": [int(current_x), int(row_y)]
                }
                parking_zones.append(zone)
                spot_id += 1

            current_x += avg_spacing

    return parking_zones


def merge_nearby_zones(zones, min_distance=30):
    """Remove duplicate/overlapping zones."""
    if len(zones) <= 1:
        return zones

    merged = []
    used = set()

    for i, zone1 in enumerate(zones):
        if i in used:
            continue

        c1 = zone1["center"]
        should_add = True

        for j, zone2 in enumerate(merged):
            c2 = zone2["center"]
            dist = np.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)
            if dist < min_distance:
                should_add = False
                break

        if should_add:
            merged.append(zone1)
            used.add(i)

    # Re-number IDs
    for i, zone in enumerate(merged):
        zone["id"] = i

    return merged


def is_point_in_polygon(point, polygon):
    """Check if point is inside polygon."""
    poly_np = np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))
    return cv2.pointPolygonTest(poly_np, point, False) >= 0


def check_zone_occupancy(zones, vehicle_boxes):
    """
    Check which zones are occupied by checking if any vehicle center
    falls within the zone, OR if the zone overlaps significantly with a vehicle box.
    """
    occupancy = [False] * len(zones)

    for box in vehicle_boxes:
        x1, y1, x2, y2 = box
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)
        box_area = (x2 - x1) * (y2 - y1)

        for idx, zone in enumerate(zones):
            if occupancy[idx]:
                continue

            # Method 1: Check if vehicle center is in zone
            if is_point_in_polygon((center_x, center_y), zone["points"]):
                occupancy[idx] = True
                continue

            # Method 2: Check for significant overlap (IoU-like)
            zp = zone["points"]
            zx1, zy1 = zp[0]
            zx2, zy2 = zp[2]

            # Calculate intersection
            ix1 = max(x1, zx1)
            iy1 = max(y1, zy1)
            ix2 = min(x2, zx2)
            iy2 = min(y2, zy2)

            if ix1 < ix2 and iy1 < iy2:
                intersection = (ix2 - ix1) * (iy2 - iy1)
                zone_area = (zx2 - zx1) * (zy2 - zy1)

                # If intersection is >30% of zone or box, consider occupied
                if intersection > 0.3 * zone_area or intersection > 0.3 * box_area:
                    occupancy[idx] = True

    return occupancy


def draw_parking_zones(frame, zones, occupancy_list):
    """Draw parking zones with green (available) / red (occupied) colors."""
    overlay = frame.copy()

    for idx, zone in enumerate(zones):
        points = np.array(zone["points"], dtype=np.int32)
        color = RED if occupancy_list[idx] else GREEN

        # Draw filled polygon with transparency
        cv2.fillPoly(overlay, [points], color)

        # Draw border
        cv2.polylines(frame, [points], isClosed=True, color=color, thickness=2)

        # Draw spot number
        center = zone["center"]
        label = f"#{idx+1}"

        # Background for text
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(frame, (center[0]-tw//2-2, center[1]-th//2-2),
                     (center[0]+tw//2+2, center[1]+th//2+2), (0,0,0), -1)
        cv2.putText(frame, label, (center[0]-tw//2, center[1]+th//2),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, WHITE, 1)

    # Blend overlay
    alpha = 0.35
    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    return frame


def draw_status_bar(frame, total, available, occupied, calibrating=False, progress=0):
    """Draw status bar at top of frame."""
    h, w = frame.shape[:2]

    # Dark background bar
    cv2.rectangle(frame, (0, 0), (w, 70), (30, 30, 30), -1)

    if calibrating:
        text = f"MAPPING PARKING LOT... {progress}/{CALIBRATION_FRAMES} frames"
        cv2.putText(frame, text, (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 1, YELLOW, 2)

        # Progress bar
        bar_w = w - 40
        progress_pct = progress / CALIBRATION_FRAMES
        cv2.rectangle(frame, (20, 55), (20 + bar_w, 65), (60, 60, 60), -1)
        cv2.rectangle(frame, (20, 55), (20 + int(bar_w * progress_pct), 65), YELLOW, -1)
    else:
        # Title
        cv2.putText(frame, "RUParked", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, WHITE, 2)

        # Stats
        cv2.putText(frame, f"SPOTS: {total}", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 1)
        cv2.putText(frame, f"AVAILABLE: {available}", (150, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, GREEN, 2)
        cv2.putText(frame, f"OCCUPIED: {occupied}", (350, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, RED, 2)

        # Availability percentage
        avail_pct = (available / total * 100) if total > 0 else 0
        pct_color = GREEN if avail_pct > 30 else YELLOW if avail_pct > 10 else RED
        cv2.putText(frame, f"{avail_pct:.0f}% FREE", (w - 150, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.8, pct_color, 2)

    return frame


# Main execution
print(f"\nStarting YOLO26 inference on: {YOUTUBE_URL}")
print(f"Phase 1: Mapping parking lot ({CALIBRATION_FRAMES} frames)")
print("=" * 60)

results = model.predict(source=YOUTUBE_URL, stream=True, show=False, verbose=False)

frame_count = 0
vehicle_positions = []  # (center_x, center_y, width, height)
parking_zones = []
calibration_complete = False
frame_shape = None

for result in results:
    frame_count += 1
    frame = result.plot()

    if frame_shape is None:
        frame_shape = frame.shape

    # Get all vehicle detections
    current_vehicles = []
    boxes = result.boxes
    for box in boxes:
        cls_id = int(box.cls[0])
        if cls_id in VEHICLE_CLASSES:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            width = x2 - x1
            height = y2 - y1

            current_vehicles.append((x1, y1, x2, y2))

            if not calibration_complete:
                vehicle_positions.append((center_x, center_y, width, height))

    # After calibration, create the parking grid
    if frame_count == CALIBRATION_FRAMES and not calibration_complete:
        print(f"\nCalibration complete. Analyzed {len(vehicle_positions)} vehicle detections.")
        print("Creating parking spot grid...")

        # Create grid from vehicle positions
        parking_zones = create_grid_from_vehicles(vehicle_positions, frame_shape)
        parking_zones = merge_nearby_zones(parking_zones, min_distance=40)

        print(f"Mapped {len(parking_zones)} parking spots!")

        # Save zones
        with open("auto_parking_zones.json", "w") as f:
            json.dump(parking_zones, f, indent=2)
        print("Saved to auto_parking_zones.json")

        calibration_complete = True
        print("\n" + "=" * 60)
        print("Phase 2: Live monitoring")
        print("=" * 60 + "\n")

    # Draw visualization
    if not calibration_complete:
        frame = draw_status_bar(frame, 0, 0, 0, calibrating=True, progress=frame_count)
    elif len(parking_zones) > 0:
        # Check occupancy
        occupancy = check_zone_occupancy(parking_zones, current_vehicles)
        occupied = sum(occupancy)
        available = len(parking_zones) - occupied

        # Draw zones
        frame = draw_parking_zones(frame, parking_zones, occupancy)
        frame = draw_status_bar(frame, len(parking_zones), available, occupied)

        # Print JSON every 30 frames
        if frame_count % 30 == 0:
            frame_data = {
                "frame_number": frame_count,
                "total_spots": len(parking_zones),
                "available": available,
                "occupied": occupied,
                "occupancy_rate": round(occupied / len(parking_zones) * 100, 1),
                "spots": [
                    {"id": i, "occupied": occupancy[i], "polygon": parking_zones[i]["points"]}
                    for i in range(len(parking_zones))
                ]
            }
            print(f"Frame {frame_count} | Available: {available}/{len(parking_zones)} | Occupied: {occupied}")

    # Display
    cv2.imshow("RUParked - Parking Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("\nQuitting...")
        break

cv2.destroyAllWindows()
print(f"\nFinished. Mapped {len(parking_zones)} total parking spots.")
