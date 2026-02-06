import json
import cv2
import numpy as np
from ultralytics import YOLO
from sklearn.cluster import DBSCAN

# Configuration
YOUTUBE_URL = "https://www.youtube.com/watch?v=U7HRKjlXK-Y"
MODEL_PATH = "yolo26n.pt"
CALIBRATION_FRAMES = 150  # Frames to observe before defining spots
MIN_SPOT_DETECTIONS = 3   # Minimum detections to consider a valid parking spot

# COCO class IDs for vehicles
VEHICLE_CLASSES = [2, 5, 7]  # car, bus, truck

# Load YOLO26 model
print(f"Loading model: {MODEL_PATH}")
model = YOLO(MODEL_PATH)


def cluster_vehicle_positions(positions, eps=50, min_samples=3):
    """
    Use DBSCAN clustering to find parking spot locations from vehicle positions.

    Args:
        positions: List of (x, y, w, h) tuples for detected vehicles
        eps: Maximum distance between points in a cluster (pixels)
        min_samples: Minimum points to form a cluster

    Returns:
        List of parking zone polygons
    """
    if len(positions) < min_samples:
        return []

    # Use center points for clustering
    centers = np.array([[p[0], p[1]] for p in positions])

    # DBSCAN clustering
    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(centers)
    labels = clustering.labels_

    # Get unique clusters (ignore noise labeled as -1)
    unique_labels = set(labels)
    unique_labels.discard(-1)

    parking_zones = []
    for label in unique_labels:
        # Get all positions in this cluster
        cluster_mask = labels == label
        cluster_positions = [positions[i] for i in range(len(positions)) if cluster_mask[i]]

        # Calculate average bounding box for this spot
        avg_x = np.mean([p[0] for p in cluster_positions])
        avg_y = np.mean([p[1] for p in cluster_positions])
        avg_w = np.mean([p[2] for p in cluster_positions])
        avg_h = np.mean([p[3] for p in cluster_positions])

        # Create polygon from bounding box (with some padding)
        padding = 10
        x1, y1 = int(avg_x - avg_w/2 - padding), int(avg_y - avg_h/2 - padding)
        x2, y2 = int(avg_x + avg_w/2 + padding), int(avg_y + avg_h/2 + padding)

        zone = {
            "points": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
            "center": [int(avg_x), int(avg_y)],
            "detections": len(cluster_positions)
        }
        parking_zones.append(zone)

    return parking_zones


def is_point_in_polygon(point, polygon):
    """Check if point is inside polygon."""
    poly_np = np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))
    return cv2.pointPolygonTest(poly_np, point, False) >= 0


print(f"\nStarting YOLO26 inference on: {YOUTUBE_URL}")
print(f"Phase 1: Calibration - Learning parking spot positions ({CALIBRATION_FRAMES} frames)")
print("=" * 60)

results = model.predict(source=YOUTUBE_URL, stream=True, show=True, verbose=False)

frame_count = 0
calibration_positions = []  # Store (center_x, center_y, width, height)
parking_zones = []
calibration_complete = False

for result in results:
    frame_count += 1

    # Get detected vehicles
    boxes = result.boxes
    for box in boxes:
        cls_id = int(box.cls[0])

        if cls_id in VEHICLE_CLASSES:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            width = x2 - x1
            height = y2 - y1

            if not calibration_complete:
                # Calibration phase: collect vehicle positions
                calibration_positions.append((center_x, center_y, width, height))

    # After calibration frames, cluster positions to find parking spots
    if frame_count == CALIBRATION_FRAMES and not calibration_complete:
        print(f"\nCalibration complete. Collected {len(calibration_positions)} vehicle detections.")
        print("Clustering to find parking spots...")

        parking_zones = cluster_vehicle_positions(
            calibration_positions,
            eps=60,  # Vehicles within 60px are same spot
            min_samples=MIN_SPOT_DETECTIONS
        )

        print(f"Detected {len(parking_zones)} parking spots automatically!")

        # Save zones to file
        with open("auto_parking_zones.json", "w") as f:
            json.dump(parking_zones, f, indent=2)
        print("Saved parking zones to auto_parking_zones.json")

        calibration_complete = True
        print("\n" + "=" * 60)
        print("Phase 2: Detection - Monitoring parking availability")
        print("=" * 60 + "\n")

    # Detection phase: check occupancy of auto-detected spots
    if calibration_complete and len(parking_zones) > 0:
        zone_occupancy = [False] * len(parking_zones)

        for box in boxes:
            cls_id = int(box.cls[0])
            if cls_id in VEHICLE_CLASSES:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)

                for idx, zone in enumerate(parking_zones):
                    if is_point_in_polygon((center_x, center_y), zone["points"]):
                        zone_occupancy[idx] = True
                        break

        occupied = sum(zone_occupancy)
        available = len(parking_zones) - occupied

        # Print status every 30 frames
        if frame_count % 30 == 0:
            frame_data = {
                "frame_number": frame_count,
                "total_spots": len(parking_zones),
                "available": available,
                "occupied": occupied,
                "occupancy_rate": round(occupied / len(parking_zones) * 100, 1),
                "spots": [
                    {
                        "id": i,
                        "occupied": zone_occupancy[i],
                        "polygon": parking_zones[i]["points"]
                    }
                    for i in range(len(parking_zones))
                ]
            }
            print(f"Frame {frame_count} | Available: {available}/{len(parking_zones)} | Occupied: {occupied}")
            print(f"  JSON: {json.dumps({k: v for k, v in frame_data.items() if k != 'spots'})}")

print(f"\nFinished. Total frames: {frame_count}")
print(f"Auto-detected {len(parking_zones)} parking spots")
