# RUParked - Parking Detection System Design

## Overview

Real-time parking lot detection using Ultralytics YOLO ParkingManagement solution. Outputs JSON data for backend integration and displays live video with occupancy overlays.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    parking_detector.py                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐ │
│  │  Download    │   │    Setup     │   │    Detection     │ │
│  │  (yt-dlp)    │   │  (GUI)       │   │    (YOLO)        │ │
│  └──────────────┘   └──────────────┘   └──────────────────┘ │
│         │                  │                   │            │
│         ▼                  ▼                   ▼            │
│  parking_lot.mp4   parking_zones.json    JSON output +      │
│                                          Live display       │
└─────────────────────────────────────────────────────────────┘
```

## Workflow

1. **Download**: Fetch YouTube video using yt-dlp
2. **Setup**: Use Ultralytics GUI to draw parking spot polygons
3. **Detect**: Run YOLO inference, output JSON, show live window

## JSON Output Format

```json
{
  "frame_number": 42,
  "timestamp_ms": 1400,
  "total_spots": 20,
  "available": 8,
  "occupied": 12,
  "occupancy_rate": 60.0
}
```

## M4 Mac Compatibility

- Uses MPS (Metal Performance Shaders) when available
- Falls back to CPU if MPS fails
- Tested with Python 3.14, ultralytics 8.4.12

## Dependencies

- ultralytics (YOLO + ParkingManagement)
- opencv-python (video display)
- yt-dlp (YouTube download)
- FFmpeg (required by yt-dlp)

## Future Backend Integration

The JSON output provides:
- `available` / `occupied` counts for UI display
- `occupancy_rate` percentage for quick status
- `timestamp_ms` for time-series tracking
- Per-spot status can be added when zones are loaded

Frontend can consume this to render:
- Green spots = available
- Red spots = occupied
- Real-time map overlay
