#!/usr/bin/env python3
"""
RUParked - Parking Lot Detection System
Uses Ultralytics YOLO26 with ParkingManagement for real-time parking spot detection.
Streams YouTube videos directly - no download required.

Usage:
    python parking_detector.py --source <youtube_url>   # Run detection with live display
    python parking_detector.py --source <youtube_url> --output data.json  # Save JSON
"""

import argparse
import json
import os
import sys
import time

import cv2
import numpy as np
from ultralytics import YOLO


# Configuration
DEFAULT_ZONES_FILE = "bounding_boxes.json"
DEFAULT_MODEL = "yolo26n.pt"


def load_parking_zones(zones_file: str) -> list:
    """Load parking zone polygons from JSON file."""
    if not os.path.exists(zones_file):
        print(f"Error: Parking zones file not found: {zones_file}")
        print("Create bounding_boxes.json with parking zone coordinates first.")
        sys.exit(1)

    with open(zones_file, 'r') as f:
        zones_data = json.load(f)

    # Format: [{"points": [[x1,y1], [x2,y2], ...]}, ...]
    if isinstance(zones_data, list):
        return zones_data
    return []


def is_point_in_polygon(point: tuple, polygon: list) -> bool:
    """Check if a point is inside a polygon using cv2.pointPolygonTest."""
    polygon_np = np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))
    return cv2.pointPolygonTest(polygon_np, point, False) >= 0


def run_parking_detection(
    source: str,
    zones_file: str = DEFAULT_ZONES_FILE,
    model_path: str = DEFAULT_MODEL,
    output_file: str = None
):
    """
    Run parking detection on YouTube stream or video file.
    Uses YOLO26 model.predict() which handles YouTube URLs directly.
    """
    # Load parking zones
    parking_zones = load_parking_zones(zones_file)
    total_spots = len(parking_zones)
    print(f"Loaded {total_spots} parking zones from {zones_file}")

    # Load YOLO26 model
    print(f"Loading model: {model_path}")
    model = YOLO(model_path)

    # Prepare output
    json_output = []
    output_handle = None
    if output_file:
        output_handle = open(output_file, 'w')
        output_handle.write('[\n')

    print(f"\nStarting YOLO26 inference on: {source}")
    print("Press 'q' in the video window to quit\n")

    frame_count = 0
    start_time = time.time()

    # Run prediction with stream=True for YouTube support
    # show=True opens a window with bounding boxes drawn
    results = model.predict(
        source=source,
        stream=True,
        show=True,
        verbose=False,
        classes=[2, 5, 7],  # car, bus, truck (COCO classes)
        conf=0.25
    )

    try:
        for result in results:
            frame_count += 1

            # Get the frame dimensions
            if hasattr(result, 'orig_shape'):
                frame_height, frame_width = result.orig_shape
            else:
                frame_height, frame_width = 720, 1280

            # Track which zones are occupied
            zone_occupancy = [False] * total_spots

            # Check each detected vehicle
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)

                # Check if vehicle center is in any parking zone
                for idx, zone in enumerate(parking_zones):
                    polygon = zone.get("points", zone)
                    if is_point_in_polygon((center_x, center_y), polygon):
                        zone_occupancy[idx] = True
                        break

            # Calculate occupancy
            occupied = sum(zone_occupancy)
            available = total_spots - occupied

            # Build JSON output
            spots_status = []
            for idx, zone in enumerate(parking_zones):
                spots_status.append({
                    "id": idx,
                    "occupied": zone_occupancy[idx],
                    "polygon": zone.get("points", zone)
                })

            frame_data = {
                "frame_number": frame_count,
                "timestamp_ms": int(frame_count * (1000 / 30)),  # Approximate
                "total_spots": total_spots,
                "available": available,
                "occupied": occupied,
                "occupancy_rate": round(occupied / total_spots * 100, 1) if total_spots > 0 else 0,
                "spots": spots_status
            }

            # Print status every 30 frames
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                print(f"Frame {frame_count} | Available: {available}/{total_spots} | "
                      f"Occupied: {occupied} | FPS: {fps:.1f}")
                print(f"  JSON: {json.dumps({k: v for k, v in frame_data.items() if k != 'spots'})}")

            # Save to output file
            if output_handle:
                if frame_count > 1:
                    output_handle.write(',\n')
                output_handle.write(json.dumps(frame_data))

            json_output.append(frame_data)

    except KeyboardInterrupt:
        print("\nStopped by user")

    finally:
        if output_handle:
            output_handle.write('\n]')
            output_handle.close()
            print(f"\nJSON output saved to: {output_file}")

        # Print summary
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print("DETECTION COMPLETE - YOLO26")
        print(f"{'='*60}")
        print(f"Processed {frame_count} frames in {elapsed:.1f}s ({frame_count/elapsed:.1f} FPS)")

        if json_output:
            last = json_output[-1]
            print(f"Final: {last['available']} available, {last['occupied']} occupied")

    return json_output


def main():
    parser = argparse.ArgumentParser(
        description="RUParked - YOLO26 Parking Detection (YouTube streaming supported)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run detection on YouTube video (opens window automatically)
  python parking_detector.py --source "https://www.youtube.com/watch?v=U7HRKjlXK-Y"

  # Run detection on local video
  python parking_detector.py --source parking_lot.mp4

  # Save JSON output
  python parking_detector.py --source "https://youtu.be/..." --output data.json
        """
    )

    parser.add_argument(
        "--source", "-s",
        required=True,
        help="Video source: YouTube URL or local file path"
    )
    parser.add_argument(
        "--zones", "-z",
        default=DEFAULT_ZONES_FILE,
        help=f"Path to parking zones JSON (default: {DEFAULT_ZONES_FILE})"
    )
    parser.add_argument(
        "--model", "-m",
        default=DEFAULT_MODEL,
        help=f"YOLO model (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--output", "-o",
        help="Save JSON output to file"
    )

    args = parser.parse_args()

    run_parking_detection(
        source=args.source,
        zones_file=args.zones,
        model_path=args.model,
        output_file=args.output
    )


if __name__ == "__main__":
    main()
