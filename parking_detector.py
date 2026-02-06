#!/usr/bin/env python3
"""
RUParked - Parking Lot Detection System
Uses Ultralytics YOLO with ParkingManagement for real-time parking spot detection.

Usage:
    python parking_detector.py --download <youtube_url>   # Download a YouTube video
    python parking_detector.py --setup                    # Launch GUI to draw parking zones
    python parking_detector.py --detect                   # Run detection with live display
    python parking_detector.py --detect --output spots.json  # Save JSON output to file
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

# Check for required dependencies
def check_dependencies():
    """Check that all required dependencies are available."""
    errors = []

    # Check FFmpeg (required for yt-dlp video merging)
    import shutil
    if not shutil.which("ffmpeg"):
        errors.append(
            "FFmpeg not found. Install it with: brew install ffmpeg"
        )

    # Check tkinter (required for ParkingPtsSelection GUI)
    try:
        import tkinter
    except ImportError:
        errors.append(
            "tkinter not found. Install Python from python.org or: brew install python-tk"
        )

    if errors:
        print("Missing dependencies:")
        for e in errors:
            print(f"  - {e}")
        print("\nPlease install the missing dependencies and try again.")
        sys.exit(1)


# Configuration
DEFAULT_VIDEO = "parking_lot.mp4"
DEFAULT_ZONES_FILE = "parking_zones.json"
DEFAULT_MODEL = "yolo11n.pt"  # Nano model for fast inference

# Sample YouTube video (parking lot with cars - replace with your own)
SAMPLE_VIDEO_URL = "https://www.youtube.com/watch?v=wqctLW0Hb_0"


def get_device():
    """Get the best available device for inference (MPS for M4 Mac, else CPU)."""
    import torch

    if torch.backends.mps.is_available():
        # Check if MPS is actually working
        try:
            test_tensor = torch.zeros(1, device="mps")
            del test_tensor
            print("Using MPS (Metal Performance Shaders) for GPU acceleration")
            return "mps"
        except Exception as e:
            print(f"MPS available but not working: {e}")
            print("Falling back to CPU")
            return "cpu"
    else:
        print("MPS not available, using CPU")
        return "cpu"


def download_video(url: str, output_path: str = DEFAULT_VIDEO) -> str:
    """Download a YouTube video using yt-dlp."""
    import yt_dlp

    print(f"Downloading video from: {url}")
    print(f"Output path: {output_path}")

    ydl_opts = {
        'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]',  # 720p max for faster processing
        'merge_output_format': 'mp4',
        'outtmpl': output_path.replace('.mp4', '') + '.%(ext)s',
        'quiet': False,
        'no_warnings': False,
        'noplaylist': True,
    }

    # Remove extension from output path if present
    base_path = output_path.replace('.mp4', '')
    final_path = base_path + '.mp4'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Find the downloaded file (might have different extension initially)
        if os.path.exists(final_path):
            print(f"Video downloaded successfully: {final_path}")
            return final_path
        else:
            # Check for webm or other formats
            for ext in ['.webm', '.mkv', '.mp4']:
                check_path = base_path + ext
                if os.path.exists(check_path):
                    print(f"Video downloaded successfully: {check_path}")
                    return check_path
            raise FileNotFoundError("Downloaded video not found")

    except Exception as e:
        print(f"Error downloading video: {e}")
        sys.exit(1)


def setup_parking_zones(video_path: str = DEFAULT_VIDEO, output_file: str = DEFAULT_ZONES_FILE):
    """Launch the Ultralytics GUI to draw parking zone polygons."""
    from ultralytics import solutions

    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        print("Please download a video first using: python parking_detector.py --download <url>")
        sys.exit(1)

    print("\n" + "="*60)
    print("PARKING ZONE SETUP")
    print("="*60)
    print("""
Instructions:
1. A window will open showing a frame from your video
2. Click to create polygon points around each parking spot
3. Right-click to complete a polygon and start a new one
4. Press 'S' to save and quit when done
5. Zones will be saved to: {}
    """.format(output_file))
    print("="*60 + "\n")

    # Extract a frame from the video for annotation
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open video: {video_path}")
        sys.exit(1)

    # Skip to 2 seconds in for a better frame
    cap.set(cv2.CAP_PROP_POS_MSEC, 2000)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Error: Cannot read frame from video")
        sys.exit(1)

    # Save frame for annotation
    frame_path = "parking_frame.png"
    cv2.imwrite(frame_path, frame)
    print(f"Extracted frame saved to: {frame_path}")

    # Launch the parking points selection GUI
    print("Launching parking zone selection GUI...")
    print("(If the GUI doesn't appear, check that you have tkinter installed)")

    try:
        solutions.ParkingPtsSelection()
        print(f"\nZones saved! Check for 'bounding_boxes.json' in current directory.")
        print("Rename it to '{}' if needed.".format(output_file))
    except Exception as e:
        print(f"Error launching GUI: {e}")
        print("\nAlternative: Create parking_zones.json manually with this format:")
        print("""
{
  "points": [
    [[x1, y1], [x2, y2], [x3, y3], [x4, y4]],
    [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
  ]
}
        """)
        sys.exit(1)


def run_detection(
    video_path: str = DEFAULT_VIDEO,
    zones_file: str = DEFAULT_ZONES_FILE,
    model_path: str = DEFAULT_MODEL,
    output_file: str = None,
    show_window: bool = True
):
    """Run parking detection on video with live display and JSON output."""
    from ultralytics import solutions

    # Validate inputs
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)

    # Check for zones file - try both names
    actual_zones_file = zones_file
    if not os.path.exists(zones_file):
        if os.path.exists("bounding_boxes.json"):
            actual_zones_file = "bounding_boxes.json"
            print(f"Using zones file: {actual_zones_file}")
        else:
            print(f"Error: Parking zones file not found: {zones_file}")
            print("Please run setup first: python parking_detector.py --setup")
            sys.exit(1)

    # Load zones to get spot count
    with open(actual_zones_file, 'r') as f:
        zones_data = json.load(f)

    # Handle different JSON formats
    if "points" in zones_data:
        spots = zones_data["points"]
    elif isinstance(zones_data, list):
        spots = zones_data
    else:
        spots = list(zones_data.values())[0] if zones_data else []

    total_spots = len(spots)
    print(f"Loaded {total_spots} parking zones from {actual_zones_file}")

    # Get device
    device = get_device()

    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open video: {video_path}")
        sys.exit(1)

    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"Video: {width}x{height} @ {fps}fps, {total_frames} frames")

    # Initialize parking manager
    print(f"Loading model: {model_path}")
    parking_manager = solutions.ParkingManagement(
        model=model_path,
        json_file=actual_zones_file,
        show=False,  # We'll handle display ourselves
    )

    print("\n" + "="*60)
    print("DETECTION RUNNING")
    print("="*60)
    print("Press 'q' to quit, 'p' to pause/resume")
    print("="*60 + "\n")

    # Prepare output file
    json_output = []
    output_handle = None
    if output_file:
        output_handle = open(output_file, 'w')
        output_handle.write('[\n')

    frame_count = 0
    paused = False
    start_time = time.time()

    try:
        while cap.isOpened():
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    print("\nEnd of video reached")
                    break

                frame_count += 1
                timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)

                # Run detection
                results = parking_manager(frame)

                # Extract occupancy info from the parking manager
                # The manager tracks which spots are occupied
                available = getattr(parking_manager, 'available', 0)
                occupied = getattr(parking_manager, 'occupied', 0)

                # If attributes not available, estimate from the total
                if available == 0 and occupied == 0:
                    # Try to get from pr_info if available
                    pr_info = getattr(parking_manager, 'pr_info', {})
                    available = pr_info.get('Available', 0)
                    occupied = pr_info.get('Occupancy', 0)

                # Build per-spot status for frontend (red/green map)
                spots_status = []
                # Get the region status from parking manager if available
                regions = getattr(parking_manager, 'json', [])
                if isinstance(regions, dict) and "points" in regions:
                    regions = regions["points"]
                elif isinstance(regions, dict):
                    regions = list(regions.values())[0] if regions else []

                # Check each region's occupancy status
                # The parking manager marks regions as occupied/available
                for idx, region in enumerate(regions):
                    # Default to available, will be updated by detection logic
                    is_occupied = False

                    # Try to get occupancy from parking manager's internal state
                    if hasattr(parking_manager, 'region_status'):
                        is_occupied = parking_manager.region_status.get(idx, False)

                    spots_status.append({
                        "id": idx,
                        "occupied": is_occupied,
                        "polygon": region if isinstance(region, list) else list(region)
                    })

                # Build JSON output for this frame
                frame_data = {
                    "frame_number": frame_count,
                    "timestamp_ms": int(timestamp_ms),
                    "total_spots": total_spots,
                    "available": available,
                    "occupied": occupied,
                    "occupancy_rate": round(occupied / total_spots * 100, 1) if total_spots > 0 else 0,
                    "spots": spots_status  # Per-spot status for frontend map
                }

                # Print status every 30 frames
                if frame_count % 30 == 0:
                    elapsed = time.time() - start_time
                    current_fps = frame_count / elapsed if elapsed > 0 else 0
                    print(f"Frame {frame_count}/{total_frames} | "
                          f"Available: {available}/{total_spots} | "
                          f"Occupied: {occupied} | "
                          f"FPS: {current_fps:.1f}")

                    # Output JSON
                    print(f"  JSON: {json.dumps(frame_data)}")

                # Save to output file
                if output_handle:
                    if frame_count > 1:
                        output_handle.write(',\n')
                    output_handle.write(json.dumps(frame_data, indent=2))

                json_output.append(frame_data)

                # Display frame
                if show_window:
                    # Get the annotated frame
                    display_frame = getattr(results, 'plot_im', frame)
                    if display_frame is None:
                        display_frame = frame

                    # Add status overlay
                    overlay_text = f"Available: {available}/{total_spots} | Occupied: {occupied}"
                    cv2.putText(
                        display_frame, overlay_text,
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1,
                        (0, 255, 0), 2
                    )

                    # Resize for display if too large
                    max_display_width = 1280
                    if display_frame.shape[1] > max_display_width:
                        scale = max_display_width / display_frame.shape[1]
                        display_frame = cv2.resize(display_frame, None, fx=scale, fy=scale)

                    cv2.imshow("RUParked - Parking Detection", display_frame)

            # Handle keyboard input
            key = cv2.waitKey(1 if not paused else 100) & 0xFF
            if key == ord('q'):
                print("\nQuitting...")
                break
            elif key == ord('p'):
                paused = not paused
                print("Paused" if paused else "Resumed")

    finally:
        cap.release()
        cv2.destroyAllWindows()

        if output_handle:
            output_handle.write('\n]')
            output_handle.close()
            print(f"\nJSON output saved to: {output_file}")

        # Print summary
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print("DETECTION COMPLETE")
        print(f"{'='*60}")
        print(f"Processed {frame_count} frames in {elapsed:.1f}s ({frame_count/elapsed:.1f} FPS)")

        if json_output:
            last_frame = json_output[-1]
            print(f"Final state: {last_frame['available']} available, {last_frame['occupied']} occupied")


def main():
    parser = argparse.ArgumentParser(
        description="RUParked - Parking Lot Detection System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download a sample parking lot video
  python parking_detector.py --download "https://www.youtube.com/watch?v=..."

  # Set up parking zones (draw polygons)
  python parking_detector.py --setup

  # Run detection with live display
  python parking_detector.py --detect

  # Run detection and save JSON output
  python parking_detector.py --detect --output parking_data.json
        """
    )

    parser.add_argument(
        "--download", "-d",
        metavar="URL",
        help="Download a YouTube video for testing"
    )
    parser.add_argument(
        "--setup", "-s",
        action="store_true",
        help="Launch GUI to draw parking zone polygons"
    )
    parser.add_argument(
        "--detect", "-r",
        action="store_true",
        help="Run detection on video"
    )
    parser.add_argument(
        "--video", "-v",
        default=DEFAULT_VIDEO,
        help=f"Path to video file (default: {DEFAULT_VIDEO})"
    )
    parser.add_argument(
        "--zones", "-z",
        default=DEFAULT_ZONES_FILE,
        help=f"Path to parking zones JSON file (default: {DEFAULT_ZONES_FILE})"
    )
    parser.add_argument(
        "--model", "-m",
        default=DEFAULT_MODEL,
        help=f"YOLO model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--output", "-o",
        help="Save JSON output to file"
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Run without display window (headless mode)"
    )

    args = parser.parse_args()

    # If no action specified, show help
    if not any([args.download, args.setup, args.detect]):
        parser.print_help()
        print("\n" + "="*60)
        print("Quick Start:")
        print("="*60)
        print("1. Download a video:  python parking_detector.py --download <youtube_url>")
        print("2. Draw parking zones: python parking_detector.py --setup")
        print("3. Run detection:      python parking_detector.py --detect")
        return

    # Check dependencies for actions that need them
    if args.download:
        # Only check FFmpeg for download
        import shutil
        if not shutil.which("ffmpeg"):
            print("FFmpeg not found. Install it with: brew install ffmpeg")
            sys.exit(1)

    # Execute requested action
    if args.download:
        download_video(args.download, args.video)

    if args.setup:
        setup_parking_zones(args.video, args.zones)

    if args.detect:
        run_detection(
            video_path=args.video,
            zones_file=args.zones,
            model_path=args.model,
            output_file=args.output,
            show_window=not args.no_display
        )


if __name__ == "__main__":
    main()
