# RUParked - Parking Lot Detection System

Real-time parking lot detection using Ultralytics YOLO11 with ParkingManagement. Outputs JSON data for backend integration and displays live video with occupancy overlays (green = available, red = occupied).

## Quick Start

```bash
# 1. Activate the virtual environment
source venv/bin/activate

# 2. Download a parking lot video from YouTube
python parking_detector.py --download "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"

# 3. Launch GUI to draw parking spot polygons
python parking_detector.py --setup

# 4. Run detection with live display
python parking_detector.py --detect

# 5. (Optional) Save JSON output for backend
python parking_detector.py --detect --output parking_data.json
```

## Features

- **YOLO11n model** - Fast nano model optimized for real-time detection
- **M4 Mac optimized** - Uses Metal Performance Shaders (MPS) for GPU acceleration
- **Live video display** - OpenCV window showing detection overlays
- **JSON output** - Per-frame and per-spot status for backend integration
- **YouTube download** - Built-in yt-dlp integration

## JSON Output Format

Each frame outputs:

```json
{
  "frame_number": 42,
  "timestamp_ms": 1400,
  "total_spots": 20,
  "available": 8,
  "occupied": 12,
  "occupancy_rate": 60.0,
  "spots": [
    {"id": 0, "occupied": true, "polygon": [[100, 200], [200, 200], [200, 300], [100, 300]]},
    {"id": 1, "occupied": false, "polygon": [[220, 200], [320, 200], [320, 300], [220, 300]]}
  ]
}
```

## Installation (Fresh Setup)

```bash
# Install FFmpeg (required for video processing)
brew install ffmpeg

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Or use the setup script:

```bash
./setup.sh
```

## CLI Options

```
--download, -d URL    Download a YouTube video
--setup, -s           Launch GUI to draw parking zones
--detect, -r          Run detection on video
--video, -v PATH      Path to video file (default: parking_lot.mp4)
--zones, -z PATH      Path to zones JSON (default: parking_zones.json)
--model, -m MODEL     YOLO model (default: yolo11n.pt)
--output, -o PATH     Save JSON output to file
--no-display          Run headless (no video window)
```

## Controls (During Detection)

- **q** - Quit
- **p** - Pause/Resume

## Recommended Test Videos

Search YouTube for:
- "parking lot surveillance footage"
- "parking lot timelapse"
- "parking garage camera"

Or use the [PKLot dataset](https://public.roboflow.com/object-detection/pklot) for static images.

## Requirements

- Python 3.10+
- macOS with Apple Silicon (M1/M2/M3/M4) or Intel
- FFmpeg
- ~500MB disk space for dependencies

## Files

```
├── parking_detector.py    # Main script
├── requirements.txt       # Python dependencies
├── setup.sh              # Installation script
├── sample_zones.json     # Example zones file
├── venv/                 # Virtual environment
└── docs/plans/           # Design documentation
```
