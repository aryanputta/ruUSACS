# RUParked - AI Vision Demo Guide

This guide explains how to run the synchronized AI Vision and Dashboard demo on any local machine.

## 📋 Prerequisites
1. **Python 3.12+**
2. **Node.js 18+**
3. **OpenCV Dependencies**: Ensure you have `libGL` or equivalent for your OS if running in a container.

## 🚀 Setup Instructions

### 1. Backend & Database
```bash
cd backend
pip install -r requirements.txt
# Database is pre-populated in git (ruparked.db)
PYTHONPATH=. uvicorn main:app --port 4000
```

### 2. AI Vision Tracker
```bash
cd vision
pip install -r requirements.txt
# Ensure live_parking_video.mp4 exists in the vision folder
python3 live_causal_tracker.py
```
> [!NOTE]
> If `live_parking_video.mp4` is missing due to git-ignore, you can use any parking lot video named appropriately.

### 3. Frontend Dashboard
```bash
# In the root directory or backend/my-app
npm install
npm run dev
```
Open [http://localhost:3000/dashboard](http://localhost:3000/dashboard) to see the live sync.

## 🛠 Features to Demo
- **Causal Sync**: Watch a car park in the vision window and see the spot flip in the dashboard.
- **Blue Trackers**: Watch a blue box drive past rows to trigger a "scanning" effect on the occupancy grid.
- **Fast Refresh**: The dashboard updates at 1Hz (every second) for immediate feedback.
