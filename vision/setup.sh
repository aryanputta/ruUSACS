#!/bin/bash
# RUParked Setup Script
# Run with: ./setup.sh

set -e

echo "=================================="
echo "RUParked - Setup Script"
echo "=================================="

# Check for Homebrew (needed for FFmpeg on Mac)
if ! command -v brew &> /dev/null; then
    echo "Homebrew not found. Please install it from https://brew.sh"
    echo "Then run this script again."
    exit 1
fi

# Check and install FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "Installing FFmpeg..."
    brew install ffmpeg
else
    echo "FFmpeg already installed ✓"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment exists ✓"
fi

# Activate and install dependencies
echo "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Download a test video:"
echo "   python parking_detector.py --download \"<youtube_url>\""
echo ""
echo "3. Set up parking zones:"
echo "   python parking_detector.py --setup"
echo ""
echo "4. Run detection:"
echo "   python parking_detector.py --detect"
echo ""
