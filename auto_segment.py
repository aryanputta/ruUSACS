"""
Auto-Segmentation Module for Parking Spot Detection

Uses SAM 3 (Segment Anything with Concepts) to automatically detect
and create bounding boxes for parking spots from video/image input.
Works for both empty and occupied parking spaces.

SAM 3 Key Advantage: Supports TEXT PROMPTS like "parking spot" to directly
find all parking spaces without manual annotation!

Model Fallback Chain: SAM 3 -> SAM 2 -> FastSAM -> YOLO-Seg

Installation (for SAM 3):
    pip install git+https://github.com/facebookresearch/sam3.git
    huggingface-cli login  # To download model checkpoints

Usage:
    python auto_segment.py --source <video_url_or_path> [--model sam3|sam2|fastsam|auto]
    python auto_segment.py --image <image_path>
    python auto_segment.py --source "https://youtube.com/..." --model sam3
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import cv2
import numpy as np
from dataclasses import dataclass


# ==================== Configuration ====================

@dataclass
class SegmentConfig:
    """Configuration for parking spot segmentation."""
    # Minimum area for a valid parking spot (pixels)
    min_spot_area: int = 2000
    # Maximum area for a valid parking spot
    max_spot_area: int = 150000
    # Aspect ratio constraints (width/height)
    min_aspect_ratio: float = 0.3
    max_aspect_ratio: float = 3.5
    # Minimum overlap to merge spots
    merge_iou_threshold: float = 0.3
    # Grid detection parameters
    grid_line_threshold: int = 50
    # SAM2 confidence threshold
    confidence_threshold: float = 0.5
    # Output file
    output_file: str = "auto_segmented_zones.json"


# ==================== Utility Functions ====================

def resolve_stream_source(source: str) -> str:
    """Resolve YouTube URLs to direct stream URL."""
    if not source or not isinstance(source, str):
        return source
    s = source.strip().lower()
    if "youtube.com" in s or "youtu.be" in s:
        try:
            import yt_dlp
            opts = {"format": "best[ext=mp4]/best", "quiet": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(source, download=False)
                if info and info.get("url"):
                    return info["url"]
                fmts = info.get("requested_formats") or []
                if fmts and fmts[0].get("url"):
                    return fmts[0]["url"]
        except Exception as e:
            print(f"yt-dlp failed to resolve YouTube URL: {e}")
    return source


def extract_frame(source: str, frame_num: int = 90) -> Optional[np.ndarray]:
    """Extract a frame from video source."""
    resolved = resolve_stream_source(source)
    cap = cv2.VideoCapture(resolved)
    
    if not cap.isOpened():
        print(f"Error: Could not open video source: {source}")
        return None
    
    # Skip to desired frame
    for _ in range(frame_num):
        ret, _ = cap.read()
        if not ret:
            break
    
    ret, frame = cap.read()
    cap.release()
    
    return frame if ret else None


def polygon_area(points: List[List[int]]) -> float:
    """Calculate area of polygon using Shoelace formula."""
    n = len(points)
    if n < 3:
        return 0
    area = 0
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2


def bbox_to_polygon(bbox: Tuple[int, int, int, int]) -> List[List[int]]:
    """Convert bounding box to polygon points."""
    x1, y1, x2, y2 = bbox
    return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]


def polygon_to_bbox(points: List[List[int]]) -> Tuple[int, int, int, int]:
    """Convert polygon to bounding box."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def compute_iou(box1: Tuple, box2: Tuple) -> float:
    """Compute Intersection over Union of two boxes."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    if x2 < x1 or y2 < y1:
        return 0.0
    
    intersection = (x2 - x1) * (y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0


# ==================== Line Detection ====================

def detect_parking_lines(frame: np.ndarray) -> Tuple[np.ndarray, List[Dict]]:
    """
    Detect parking lot lines using edge detection and Hough transform.
    Returns line mask and list of detected lines.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Enhance contrast
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # Detect white lines (parking markings)
    _, white_mask = cv2.threshold(enhanced, 180, 255, cv2.THRESH_BINARY)
    
    # Detect yellow lines
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    yellow_lower = np.array([15, 50, 50])
    yellow_upper = np.array([35, 255, 255])
    yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
    
    # Combine masks
    line_mask = cv2.bitwise_or(white_mask, yellow_mask)
    
    # Morphological operations to clean up
    kernel = np.ones((3, 3), np.uint8)
    line_mask = cv2.morphologyEx(line_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    line_mask = cv2.morphologyEx(line_mask, cv2.MORPH_OPEN, kernel)
    
    # Edge detection
    edges = cv2.Canny(line_mask, 50, 150, apertureSize=3)
    
    # Hough line detection
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, 
                            minLineLength=30, maxLineGap=20)
    
    line_list = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            
            line_list.append({
                'start': (x1, y1),
                'end': (x2, y2),
                'midpoint': ((x1 + x2) // 2, (y1 + y2) // 2),
                'angle': angle,
                'length': length
            })
    
    return line_mask, line_list


def cluster_parallel_lines(lines: List[Dict], angle_tolerance: float = 15) -> List[List[Dict]]:
    """Group lines by similar angles (parallel lines)."""
    if not lines:
        return []
    
    # Normalize angles to 0-180 range
    for line in lines:
        angle = line['angle']
        if angle < 0:
            angle += 180
        line['normalized_angle'] = angle % 180
    
    # Cluster by angle
    clusters = []
    used = set()
    
    for i, line in enumerate(lines):
        if i in used:
            continue
        
        cluster = [line]
        used.add(i)
        
        for j, other in enumerate(lines):
            if j in used:
                continue
            
            angle_diff = abs(line['normalized_angle'] - other['normalized_angle'])
            if angle_diff > 90:
                angle_diff = 180 - angle_diff
            
            if angle_diff < angle_tolerance:
                cluster.append(other)
                used.add(j)
        
        if len(cluster) >= 2:
            clusters.append(cluster)
    
    return clusters


# ==================== SAM 3 Segmentation ====================

class SAM3Segmenter:
    """
    Segment Anything Model 3 (SAM 3) wrapper for parking spot detection.
    
    SAM 3 is Meta's latest foundation model (Nov 2025) that supports:
    - Text prompts (e.g., "parking spot", "car", "empty parking space")
    - Visual prompts (points, boxes, masks)
    - Video segmentation and tracking
    
    Key advantage: Can directly prompt with "parking spot" to find all parking spaces!
    
    Install: pip install git+https://github.com/facebookresearch/sam3.git
    Requires: Python 3.12+, PyTorch 2.7+, CUDA 12.6+
    """
    
    def __init__(self):
        self.model = None
        self.processor = None
        self._load_model()
    
    def _load_model(self):
        """Load SAM 3 model."""
        try:
            from sam3.model_builder import build_sam3_image_model
            from sam3.model.sam3_image_processor import Sam3Processor
            
            print("Loading SAM 3 model (this may take a moment)...")
            self.model = build_sam3_image_model()
            self.processor = Sam3Processor(self.model)
            print("SAM 3 model loaded successfully!")
            
        except ImportError as e:
            print(f"SAM 3 not available: {e}")
            print("Install with: pip install git+https://github.com/facebookresearch/sam3.git")
            print("Requires: Python 3.12+, PyTorch 2.7+, CUDA 12.6+")
            raise
    
    def segment_with_text(self, image: np.ndarray, 
                          prompt: str = "parking spot") -> List[Dict]:
        """
        Segment image using text prompt.
        
        This is SAM 3's killer feature - you can prompt with natural language
        like "parking spot" and it will find ALL matching instances!
        
        Args:
            image: Input image (BGR format from OpenCV)
            prompt: Text description of what to segment
            
        Returns:
            List of detected regions with masks, boxes, and scores
        """
        from PIL import Image
        
        # Convert BGR to RGB for SAM 3
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        
        # Set the image
        inference_state = self.processor.set_image(pil_image)
        
        # Run text-prompted segmentation
        output = self.processor.set_text_prompt(
            state=inference_state, 
            prompt=prompt
        )
        
        masks = output["masks"]
        boxes = output["boxes"]
        scores = output["scores"]
        
        results = []
        for i in range(len(masks)):
            mask = masks[i]
            if hasattr(mask, 'cpu'):
                mask = mask.cpu().numpy()
            mask = mask.astype(np.uint8)
            
            box = boxes[i]
            if hasattr(box, 'cpu'):
                box = box.cpu().numpy()
            
            score = scores[i]
            if hasattr(score, 'item'):
                score = score.item()
            
            # Convert box from [x1, y1, x2, y2] to [x, y, w, h]
            x1, y1, x2, y2 = box
            bbox = [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]
            
            results.append({
                'mask': mask,
                'bbox': bbox,
                'area': int(mask.sum()),
                'score': float(score),
                'prompt': prompt
            })
        
        return results
    
    def segment_parking_spots(self, image: np.ndarray) -> List[Dict]:
        """
        Specialized method to detect parking spots using multiple prompts.
        Combines results from different text prompts for best coverage.
        """
        all_results = []
        
        # Try multiple prompts to maximize detection
        prompts = [
            "parking spot",
            "parking space", 
            "empty parking spot",
            "car parking bay",
            "vehicle parking area"
        ]
        
        for prompt in prompts:
            try:
                print(f"  Trying prompt: '{prompt}'...")
                results = self.segment_with_text(image, prompt)
                print(f"    Found {len(results)} segments")
                all_results.extend(results)
            except Exception as e:
                print(f"    Prompt '{prompt}' failed: {e}")
        
        return all_results
    
    def segment_vehicles(self, image: np.ndarray) -> List[Dict]:
        """Detect vehicles to identify occupied spots."""
        vehicle_prompts = ["car", "vehicle", "truck", "bus"]
        all_results = []
        
        for prompt in vehicle_prompts:
            try:
                results = self.segment_with_text(image, prompt)
                for r in results:
                    r['is_vehicle'] = True
                all_results.extend(results)
            except:
                pass
        
        return all_results


# ==================== SAM2 Fallback ====================

class SAM2Segmenter:
    """
    Segment Anything Model 2 wrapper - fallback if SAM 3 not available.
    """
    
    def __init__(self, model_type: str = "sam2_hiera_small"):
        self.model = None
        self.predictor = None
        self.model_type = model_type
        self._load_model()
    
    def _load_model(self):
        """Load SAM2 model."""
        try:
            from sam2.build_sam import build_sam2
            from sam2.sam2_image_predictor import SAM2ImagePredictor
            
            checkpoint_map = {
                "sam2_hiera_tiny": "sam2_hiera_tiny.pt",
                "sam2_hiera_small": "sam2_hiera_small.pt", 
                "sam2_hiera_base_plus": "sam2_hiera_base_plus.pt",
                "sam2_hiera_large": "sam2_hiera_large.pt",
            }
            
            checkpoint = checkpoint_map.get(self.model_type, "sam2_hiera_small.pt")
            config = f"sam2_{self.model_type.split('_')[-1]}.yaml"
            
            self.model = build_sam2(config, checkpoint)
            self.predictor = SAM2ImagePredictor(self.model)
            print(f"Loaded SAM2 model: {self.model_type}")
            
        except ImportError:
            print("SAM2 not available, falling back to MobileSAM...")
            self._load_mobilesam()
    
    def _load_mobilesam(self):
        """Load MobileSAM as fallback."""
        try:
            from ultralytics import SAM
            self.model = SAM("mobile_sam.pt")
            self.predictor = None
            print("Loaded MobileSAM via ultralytics")
        except Exception as e:
            print(f"Error loading MobileSAM: {e}")
            raise RuntimeError("No SAM model available.")
    
    def segment_image(self, image: np.ndarray, 
                      points: Optional[List[Tuple[int, int]]] = None,
                      boxes: Optional[List[Tuple[int, int, int, int]]] = None,
                      auto_mode: bool = True) -> List[Dict]:
        """Segment image using SAM2 or MobileSAM."""
        results = []
        
        if self.predictor is not None:
            self.predictor.set_image(image)
            
            if auto_mode:
                from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
                mask_generator = SAM2AutomaticMaskGenerator(self.model)
                masks = mask_generator.generate(image)
                
                for mask_data in masks:
                    results.append({
                        'mask': mask_data['segmentation'],
                        'bbox': mask_data['bbox'],
                        'area': mask_data['area'],
                        'score': mask_data['predicted_iou']
                    })
        else:
            # Ultralytics MobileSAM API
            if auto_mode:
                sam_results = self.model(image, device='cpu')
                for r in sam_results:
                    if r.masks is not None:
                        for i, mask in enumerate(r.masks.data):
                            mask_np = mask.cpu().numpy().astype(np.uint8)
                            y_indices, x_indices = np.where(mask_np)
                            if len(x_indices) > 0:
                                bbox = [int(x_indices.min()), int(y_indices.min()),
                                       int(x_indices.max() - x_indices.min()),
                                       int(y_indices.max() - y_indices.min())]
                                results.append({
                                    'mask': mask_np,
                                    'bbox': bbox,
                                    'area': int(mask_np.sum()),
                                    'score': 0.8
                                })
        
        return results


# ==================== YOLO-Seg Fallback ====================

class YOLOSegmenter:
    """
    YOLO-Seg wrapper - simplest fallback using YOLO's built-in segmentation.
    Most reliable option that works out of the box with ultralytics.
    """
    
    def __init__(self, model_name: str = "yolov8n-seg.pt"):
        self.model = None
        self.model_name = model_name
        self._load_model()
    
    def _load_model(self):
        """Load YOLO-Seg model."""
        from ultralytics import YOLO
        self.model = YOLO(self.model_name)
        print(f"Loaded YOLO-Seg model: {self.model_name}")
    
    def segment_image(self, image: np.ndarray, 
                      conf: float = 0.25) -> List[Dict]:
        """
        Segment image using YOLO-Seg.
        Returns vehicle segments which we use to identify parking spots.
        """
        results = []
        VEHICLE_CLASSES = [2, 5, 7]  # car, bus, truck
        
        outputs = self.model(image, conf=conf, verbose=False)
        
        for output in outputs:
            if output.masks is not None and output.boxes is not None:
                masks = output.masks.data.cpu().numpy()
                boxes = output.boxes
                
                for i, (mask, box) in enumerate(zip(masks, boxes)):
                    cls_id = int(box.cls[0])
                    
                    # Only keep vehicle detections
                    if cls_id not in VEHICLE_CLASSES:
                        continue
                    
                    mask_np = mask.astype(np.uint8)
                    bbox = box.xyxy[0].cpu().numpy()
                    
                    results.append({
                        'mask': mask_np,
                        'bbox': [int(bbox[0]), int(bbox[1]),
                                int(bbox[2] - bbox[0]), int(bbox[3] - bbox[1])],
                        'area': int(mask_np.sum()),
                        'score': float(box.conf[0]),
                        'class': cls_id
                    })
        
        return results


# ==================== Ground Plane Detection ====================

class GroundPlaneDetector:
    """
    Detect parking lot ground plane and markings.
    Uses color segmentation and morphological operations.
    """
    
    @staticmethod
    def detect_pavement(image: np.ndarray) -> np.ndarray:
        """Detect asphalt/concrete pavement areas."""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Asphalt is typically dark gray
        gray_lower = np.array([0, 0, 30])
        gray_upper = np.array([180, 50, 150])
        gray_mask = cv2.inRange(hsv, gray_lower, gray_upper)
        
        # Concrete is lighter gray
        concrete_lower = np.array([0, 0, 100])
        concrete_upper = np.array([180, 30, 200])
        concrete_mask = cv2.inRange(hsv, concrete_lower, concrete_upper)
        
        # Combine
        pavement_mask = cv2.bitwise_or(gray_mask, concrete_mask)
        
        # Clean up
        kernel = np.ones((15, 15), np.uint8)
        pavement_mask = cv2.morphologyEx(pavement_mask, cv2.MORPH_CLOSE, kernel)
        pavement_mask = cv2.morphologyEx(pavement_mask, cv2.MORPH_OPEN, kernel)
        
        return pavement_mask
    
    @staticmethod
    def detect_line_markings(image: np.ndarray) -> np.ndarray:
        """Detect white/yellow parking line markings."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Adaptive thresholding for line detection
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # White lines
        _, white_mask = cv2.threshold(enhanced, 200, 255, cv2.THRESH_BINARY)
        
        # Yellow lines
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        yellow_lower = np.array([15, 80, 80])
        yellow_upper = np.array([35, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
        
        # Combine
        line_mask = cv2.bitwise_or(white_mask, yellow_mask)
        
        # Thin morphological operations to preserve lines
        kernel = np.ones((3, 3), np.uint8)
        line_mask = cv2.morphologyEx(line_mask, cv2.MORPH_CLOSE, kernel)
        
        return line_mask
    
    @staticmethod
    def find_parking_grid(line_mask: np.ndarray, 
                          min_spacing: int = 50,
                          max_spacing: int = 300) -> List[Dict]:
        """
        Analyze line mask to find regular parking grid pattern.
        Returns list of detected parking spot regions.
        """
        h, w = line_mask.shape
        spots = []
        
        # Find horizontal and vertical line projections
        h_proj = np.sum(line_mask, axis=1)  # Sum along rows
        v_proj = np.sum(line_mask, axis=0)  # Sum along columns
        
        # Find peaks in projections (line positions)
        def find_peaks(projection, threshold_ratio=0.3):
            threshold = projection.max() * threshold_ratio
            peaks = []
            in_peak = False
            peak_start = 0
            
            for i, val in enumerate(projection):
                if val > threshold and not in_peak:
                    in_peak = True
                    peak_start = i
                elif val <= threshold and in_peak:
                    in_peak = False
                    peaks.append((peak_start + i) // 2)
            
            return peaks
        
        h_lines = find_peaks(h_proj)
        v_lines = find_peaks(v_proj)
        
        # Create grid from intersections
        for i in range(len(h_lines) - 1):
            for j in range(len(v_lines) - 1):
                y1, y2 = h_lines[i], h_lines[i + 1]
                x1, x2 = v_lines[j], v_lines[j + 1]
                
                # Check spacing constraints
                cell_w = x2 - x1
                cell_h = y2 - y1
                
                if (min_spacing < cell_w < max_spacing and 
                    min_spacing < cell_h < max_spacing):
                    spots.append({
                        'points': [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
                        'center': [(x1 + x2) // 2, (y1 + y2) // 2],
                        'width': cell_w,
                        'height': cell_h,
                        'from_grid': True
                    })
        
        return spots


# ==================== FastSAM Segmentation ====================

class FastSAMSegmenter:
    """
    FastSAM wrapper - faster CNN-based alternative to SAM.
    Better for real-time applications.
    """
    
    def __init__(self, model_path: str = "FastSAM-x.pt"):
        self.model = None
        self.model_path = model_path
        self._load_model()
    
    def _load_model(self):
        """Load FastSAM model."""
        try:
            from ultralytics import YOLO
            
            # Try to load FastSAM
            # Download from: https://github.com/CASIA-IVA-Lab/FastSAM
            model_file = Path(self.model_path)
            if not model_file.exists():
                print(f"FastSAM model not found at {self.model_path}")
                print("Downloading FastSAM-x...")
                # FastSAM uses YOLO architecture
                self.model = YOLO("FastSAM-x.pt")
            else:
                self.model = YOLO(self.model_path)
            
            print(f"Loaded FastSAM model")
            
        except Exception as e:
            print(f"Error loading FastSAM: {e}")
            raise
    
    def segment_image(self, image: np.ndarray, 
                      conf: float = 0.4,
                      iou: float = 0.9) -> List[Dict]:
        """
        Segment image using FastSAM.
        
        Args:
            image: Input image (BGR)
            conf: Confidence threshold
            iou: IOU threshold for NMS
            
        Returns:
            List of detected regions with masks and bounding boxes
        """
        results = []
        
        # Run FastSAM inference
        outputs = self.model(image, conf=conf, iou=iou, retina_masks=True)
        
        for output in outputs:
            if output.masks is not None:
                masks = output.masks.data.cpu().numpy()
                boxes = output.boxes.xyxy.cpu().numpy() if output.boxes is not None else []
                
                for i, mask in enumerate(masks):
                    mask_np = mask.astype(np.uint8)
                    y_indices, x_indices = np.where(mask_np)
                    
                    if len(x_indices) > 0:
                        if i < len(boxes):
                            bbox = boxes[i]
                            bbox = [int(bbox[0]), int(bbox[1]),
                                   int(bbox[2] - bbox[0]), int(bbox[3] - bbox[1])]
                        else:
                            bbox = [int(x_indices.min()), int(y_indices.min()),
                                   int(x_indices.max() - x_indices.min()),
                                   int(y_indices.max() - y_indices.min())]
                        
                        results.append({
                            'mask': mask_np,
                            'bbox': bbox,
                            'area': int(mask_np.sum()),
                            'score': float(output.boxes.conf[i]) if i < len(output.boxes.conf) else 0.8
                        })
        
        return results


# ==================== Parking Spot Detection ====================

class ParkingSpotDetector:
    """
    Main class for automatic parking spot detection using segmentation.
    
    Uses SAM 3 (Segment Anything with Concepts) as primary model - 
    it can directly understand "parking spot" text prompts!
    
    Fallback chain: SAM 3 -> SAM 2 -> FastSAM -> YOLO-Seg
    """
    
    def __init__(self, model_type: str = "sam3", config: SegmentConfig = None):
        self.config = config or SegmentConfig()
        self.segmenter = None
        self.sam3_segmenter = None  # Separate for text-prompted segmentation
        self.model_type = model_type
        self.ground_detector = GroundPlaneDetector()
        self._init_segmenter()
    
    def _init_segmenter(self):
        """Initialize the segmentation model with fallback chain."""
        segmenter_loaded = False
        
        # Try SAM 3 first (best for parking spots due to text prompts)
        if self.model_type in ["sam3", "auto"]:
            try:
                self.sam3_segmenter = SAM3Segmenter()
                self.segmenter = self.sam3_segmenter
                self.model_type = "sam3"
                segmenter_loaded = True
                print("Using SAM 3 with text-prompted segmentation!")
            except Exception as e:
                print(f"SAM 3 not available: {e}")
        
        # Try FastSAM
        if not segmenter_loaded and self.model_type in ["fastsam", "auto"]:
            try:
                self.segmenter = FastSAMSegmenter()
                self.model_type = "fastsam"
                segmenter_loaded = True
            except Exception as e:
                print(f"FastSAM failed: {e}")
        
        # Try SAM 2
        if not segmenter_loaded and self.model_type in ["sam2", "auto"]:
            try:
                self.segmenter = SAM2Segmenter()
                self.model_type = "sam2"
                segmenter_loaded = True
            except Exception as e:
                print(f"SAM2 failed: {e}")
        
        # Final fallback: YOLO-Seg (always available with ultralytics)
        if not segmenter_loaded:
            print("Using YOLO-Seg fallback...")
            try:
                self.segmenter = YOLOSegmenter()
                self.model_type = "yolo-seg"
                segmenter_loaded = True
            except Exception as e:
                print(f"YOLO-Seg failed: {e}")
                raise RuntimeError("No segmentation model available!")
    
    def detect_spots_from_segments(self, image: np.ndarray) -> List[Dict]:
        """
        Detect parking spots using segmentation.
        
        If SAM 3 is available, uses text prompts like "parking spot" for
        direct semantic understanding. Otherwise falls back to auto-segmentation.
        """
        h, w = image.shape[:2]
        
        # Use SAM 3 text prompting if available (best method!)
        if self.sam3_segmenter is not None:
            print("Using SAM 3 text-prompted segmentation...")
            segments = self.sam3_segmenter.segment_parking_spots(image)
            print(f"SAM 3 found {len(segments)} parking spot segments")
        else:
            # Fallback to auto-segmentation
            print("Running auto-segmentation...")
            segments = self.segmenter.segment_image(image, auto_mode=True)
            print(f"Found {len(segments)} segments")
        
        # Filter segments that look like parking spots
        candidates = []
        for seg in segments:
            area = seg['area']
            bbox = seg['bbox']  # [x, y, w, h]
            
            # Check area constraints
            if area < self.config.min_spot_area or area > self.config.max_spot_area:
                continue
            
            # Check aspect ratio
            if bbox[2] > 0 and bbox[3] > 0:
                aspect = bbox[2] / bbox[3]
                if aspect < self.config.min_aspect_ratio or aspect > self.config.max_aspect_ratio:
                    continue
            
            # Convert bbox from [x, y, w, h] to [x1, y1, x2, y2]
            x1, y1 = bbox[0], bbox[1]
            x2, y2 = bbox[0] + bbox[2], bbox[1] + bbox[3]
            
            candidates.append({
                'points': [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
                'center': [(x1 + x2) // 2, (y1 + y2) // 2],
                'width': bbox[2],
                'height': bbox[3],
                'area': area,
                'score': seg['score']
            })
        
        return candidates
    
    def detect_spots_from_lines(self, image: np.ndarray) -> List[Dict]:
        """
        Detect parking spots from line markings.
        Creates spots between parallel lines.
        """
        h, w = image.shape[:2]
        
        # Detect lines
        print("Detecting parking lines...")
        line_mask, lines = detect_parking_lines(image)
        print(f"Found {len(lines)} lines")
        
        if len(lines) < 4:
            return []
        
        # Cluster parallel lines
        clusters = cluster_parallel_lines(lines)
        print(f"Found {len(clusters)} line clusters")
        
        spots = []
        
        # For each cluster of parallel lines, create spots between them
        for cluster in clusters:
            # Sort lines by perpendicular distance from origin
            main_angle = np.mean([l['normalized_angle'] for l in cluster])
            
            # Group into roughly horizontal or vertical
            if 45 < main_angle < 135:
                # Mostly horizontal - sort by y
                sorted_lines = sorted(cluster, key=lambda l: l['midpoint'][1])
            else:
                # Mostly vertical - sort by x
                sorted_lines = sorted(cluster, key=lambda l: l['midpoint'][0])
            
            # Create spots between adjacent lines
            for i in range(len(sorted_lines) - 1):
                line1 = sorted_lines[i]
                line2 = sorted_lines[i + 1]
                
                # Calculate spot boundaries
                x1 = min(line1['start'][0], line1['end'][0], line2['start'][0], line2['end'][0])
                y1 = min(line1['start'][1], line1['end'][1], line2['start'][1], line2['end'][1])
                x2 = max(line1['start'][0], line1['end'][0], line2['start'][0], line2['end'][0])
                y2 = max(line1['start'][1], line1['end'][1], line2['start'][1], line2['end'][1])
                
                spot_w = x2 - x1
                spot_h = y2 - y1
                area = spot_w * spot_h
                
                # Validate spot dimensions
                if (self.config.min_spot_area < area < self.config.max_spot_area and
                    self.config.min_aspect_ratio < spot_w / max(spot_h, 1) < self.config.max_aspect_ratio):
                    
                    spots.append({
                        'points': [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
                        'center': [(x1 + x2) // 2, (y1 + y2) // 2],
                        'width': spot_w,
                        'height': spot_h,
                        'from_lines': True
                    })
        
        return spots
    
    def detect_spots_grid_based(self, image: np.ndarray, 
                                  vehicle_detections: List[Tuple] = None) -> List[Dict]:
        """
        Detect parking spots using grid-based approach.
        Uses vehicle detections as anchors and extrapolates grid.
        """
        h, w = image.shape[:2]
        spots = []
        
        if not vehicle_detections or len(vehicle_detections) < 2:
            return spots
        
        # Calculate average vehicle size
        widths = [d[2] - d[0] for d in vehicle_detections]
        heights = [d[3] - d[1] for d in vehicle_detections]
        avg_width = np.median(widths)
        avg_height = np.median(heights)
        
        # Add padding for spot size
        spot_width = int(avg_width * 1.15)
        spot_height = int(avg_height * 1.15)
        
        # Find grid alignment from vehicle centers
        centers = [((d[0] + d[2]) / 2, (d[1] + d[3]) / 2) for d in vehicle_detections]
        
        # Group by rows (similar Y coordinates)
        from sklearn.cluster import DBSCAN
        
        y_coords = np.array([[c[1]] for c in centers])
        row_clustering = DBSCAN(eps=spot_height * 0.5, min_samples=1).fit(y_coords)
        
        rows = {}
        for idx, label in enumerate(row_clustering.labels_):
            if label not in rows:
                rows[label] = []
            rows[label].append(centers[idx])
        
        # For each row, detect spacing and fill gaps
        for row_centers in rows.values():
            row_centers = sorted(row_centers, key=lambda c: c[0])
            avg_y = np.mean([c[1] for c in row_centers])
            
            if len(row_centers) >= 2:
                # Calculate spacing
                spacings = [row_centers[i+1][0] - row_centers[i][0] 
                           for i in range(len(row_centers) - 1)]
                avg_spacing = np.median(spacings)
                
                # Start from first detected vehicle
                start_x = row_centers[0][0]
                
                # Extrapolate left
                x = start_x - avg_spacing
                while x > spot_width / 2:
                    spots.append(self._create_spot(x, avg_y, spot_width, spot_height, True))
                    x -= avg_spacing
                
                # Fill in the row
                for i in range(len(row_centers)):
                    # Add detected position
                    spots.append(self._create_spot(
                        row_centers[i][0], avg_y, spot_width, spot_height, False
                    ))
                    
                    # Check for gaps
                    if i < len(row_centers) - 1:
                        gap = row_centers[i+1][0] - row_centers[i][0]
                        if gap > avg_spacing * 1.5:
                            # Fill the gap
                            num_spots = int(round(gap / avg_spacing)) - 1
                            for j in range(1, num_spots + 1):
                                fill_x = row_centers[i][0] + (j * gap / (num_spots + 1))
                                spots.append(self._create_spot(
                                    fill_x, avg_y, spot_width, spot_height, True
                                ))
                
                # Extrapolate right
                x = row_centers[-1][0] + avg_spacing
                while x < w - spot_width / 2:
                    spots.append(self._create_spot(x, avg_y, spot_width, spot_height, True))
                    x += avg_spacing
        
        return spots
    
    def _create_spot(self, cx: float, cy: float, 
                     width: int, height: int, inferred: bool) -> Dict:
        """Create a spot dictionary."""
        x1 = int(cx - width / 2)
        y1 = int(cy - height / 2)
        x2 = int(cx + width / 2)
        y2 = int(cy + height / 2)
        
        return {
            'points': [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
            'center': [int(cx), int(cy)],
            'width': width,
            'height': height,
            'inferred': inferred
        }
    
    def detect_spots_from_ground_markings(self, image: np.ndarray) -> List[Dict]:
        """
        Detect parking spots from ground plane analysis.
        Uses line marking detection and grid pattern recognition.
        """
        print("  Analyzing ground plane markings...")
        
        # Detect line markings
        line_mask = self.ground_detector.detect_line_markings(image)
        
        # Find grid pattern from lines
        grid_spots = self.ground_detector.find_parking_grid(
            line_mask, 
            min_spacing=40,
            max_spacing=350
        )
        
        return grid_spots
    
    def detect_spots_hybrid(self, image: np.ndarray,
                           use_yolo: bool = True) -> List[Dict]:
        """
        Hybrid approach combining multiple detection methods:
        1. Ground marking analysis (most reliable for parking lots)
        2. SAM/YOLO segmentation for vehicle detection
        3. Line detection for spot boundaries
        4. YOLO vehicle detection for occupied spots
        5. Grid extrapolation for complete coverage
        """
        h, w = image.shape[:2]
        all_spots = []
        
        # Method 1: Ground marking detection (most reliable)
        print("\n[1/5] Analyzing ground markings...")
        try:
            ground_spots = self.detect_spots_from_ground_markings(image)
            print(f"  Found {len(ground_spots)} spots from ground analysis")
            all_spots.extend(ground_spots)
        except Exception as e:
            print(f"  Ground analysis failed: {e}")
        
        # Method 2: Segmentation-based detection
        print("\n[2/5] Running segmentation...")
        try:
            seg_spots = self.detect_spots_from_segments(image)
            print(f"  Found {len(seg_spots)} spots from segmentation")
            all_spots.extend(seg_spots)
        except Exception as e:
            print(f"  Segmentation failed: {e}")
        
        # Method 3: Line-based detection  
        print("\n[3/5] Detecting from line markings...")
        try:
            line_spots = self.detect_spots_from_lines(image)
            print(f"  Found {len(line_spots)} spots from lines")
            all_spots.extend(line_spots)
        except Exception as e:
            print(f"  Line detection failed: {e}")
        
        # Method 4: YOLO vehicle detection
        vehicle_detections = []
        if use_yolo:
            print("\n[4/5] Running YOLO vehicle detection...")
            try:
                from ultralytics import YOLO
                # Try custom model first, fallback to pretrained
                try:
                    model = YOLO("yolo26n.pt")
                except:
                    model = YOLO("yolov8n.pt")
                    
                results = model(image, verbose=False)
                
                VEHICLE_CLASSES = [2, 5, 7]  # car, bus, truck
                for box in results[0].boxes:
                    if int(box.cls[0]) in VEHICLE_CLASSES:
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        vehicle_detections.append((int(x1), int(y1), int(x2), int(y2)))
                
                print(f"  Found {len(vehicle_detections)} vehicles")
                
                # Add spots from vehicle detections (with padding)
                for vd in vehicle_detections:
                    vw, vh = vd[2] - vd[0], vd[3] - vd[1]
                    # Add 15% padding for parking spot bounds
                    pad_w, pad_h = int(vw * 0.15), int(vh * 0.15)
                    x1, y1 = vd[0] - pad_w, vd[1] - pad_h
                    x2, y2 = vd[2] + pad_w, vd[3] + pad_h
                    
                    all_spots.append({
                        'points': [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
                        'center': [(x1 + x2) // 2, (y1 + y2) // 2],
                        'width': x2 - x1,
                        'height': y2 - y1,
                        'has_vehicle': True
                    })
            except Exception as e:
                print(f"  YOLO detection failed: {e}")
        
        # Method 5: Grid extrapolation
        print("\n[5/5] Extrapolating grid from vehicles...")
        try:
            grid_spots = self.detect_spots_grid_based(image, vehicle_detections)
            print(f"  Extrapolated {len(grid_spots)} spots from grid")
            all_spots.extend(grid_spots)
        except Exception as e:
            print(f"  Grid extrapolation failed: {e}")
        
        # Merge overlapping spots
        print(f"\nMerging {len(all_spots)} total candidates...")
        merged_spots = self._merge_spots(all_spots)
        print(f"Final: {len(merged_spots)} unique spots")
        
        # Assign IDs
        for i, spot in enumerate(merged_spots):
            spot['id'] = i
        
        return merged_spots
    
    def _merge_spots(self, spots: List[Dict]) -> List[Dict]:
        """Merge overlapping spots, preferring non-inferred ones."""
        if len(spots) <= 1:
            return spots
        
        # Sort: non-inferred first, then by score/area
        spots = sorted(spots, key=lambda s: (
            s.get('inferred', False),
            -s.get('score', 0.5),
            -s.get('area', 0)
        ))
        
        merged = []
        for spot in spots:
            bbox1 = polygon_to_bbox(spot['points'])
            
            is_duplicate = False
            for existing in merged:
                bbox2 = polygon_to_bbox(existing['points'])
                iou = compute_iou(bbox1, bbox2)
                
                if iou > self.config.merge_iou_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                merged.append(spot)
        
        return merged


# ==================== Interactive Visualizer ====================

class SpotVisualizer:
    """Interactive visualizer for reviewing and editing detected spots."""
    
    def __init__(self, image: np.ndarray, spots: List[Dict]):
        self.original = image.copy()
        self.image = image.copy()
        self.spots = spots
        self.selected_idx = -1
        self.drawing_new = False
        self.new_polygon = []
    
    def draw(self):
        """Draw all spots on image."""
        self.image = self.original.copy()
        overlay = self.image.copy()
        
        for i, spot in enumerate(self.spots):
            pts = np.array(spot['points'], dtype=np.int32)
            
            # Color based on type
            if spot.get('has_vehicle'):
                color = (0, 0, 255)  # Red - occupied
            elif spot.get('inferred'):
                color = (0, 255, 255)  # Yellow - inferred
            else:
                color = (0, 255, 0)  # Green - detected
            
            # Highlight selected
            if i == self.selected_idx:
                color = (255, 0, 255)  # Magenta
                cv2.polylines(self.image, [pts], True, color, 3)
            else:
                cv2.polylines(self.image, [pts], True, color, 2)
            
            cv2.fillPoly(overlay, [pts], color)
            
            # Draw ID
            cx, cy = spot['center']
            cv2.putText(self.image, f"#{i}", (cx-15, cy+5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        self.image = cv2.addWeighted(overlay, 0.3, self.image, 0.7, 0)
        
        # Draw new polygon in progress
        if self.new_polygon:
            pts = np.array(self.new_polygon, dtype=np.int32)
            for pt in self.new_polygon:
                cv2.circle(self.image, tuple(pt), 5, (255, 255, 0), -1)
            if len(self.new_polygon) > 1:
                cv2.polylines(self.image, [pts], False, (255, 255, 0), 2)
        
        # Draw instructions
        self._draw_instructions()
        
        return self.image
    
    def _draw_instructions(self):
        """Draw instruction overlay."""
        h, w = self.image.shape[:2]
        cv2.rectangle(self.image, (0, 0), (w, 90), (30, 30, 30), -1)
        
        cv2.putText(self.image, "AUTO-SEGMENTED PARKING SPOTS - Review Mode", 
                   (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(self.image, 
                   f"Spots: {len(self.spots)} | Click to select | 'D' delete | 'N' new | 'S' save | 'Q' quit",
                   (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        
        legend = "Green=Detected | Yellow=Inferred | Red=Has Vehicle"
        cv2.putText(self.image, legend, (10, 75), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    
    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse events."""
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.drawing_new:
                self.new_polygon.append([x, y])
            else:
                # Check if clicking on a spot
                for i, spot in enumerate(self.spots):
                    pts = np.array(spot['points'], dtype=np.int32)
                    if cv2.pointPolygonTest(pts, (x, y), False) >= 0:
                        self.selected_idx = i
                        break
                else:
                    self.selected_idx = -1
        
        elif event == cv2.EVENT_RBUTTONDOWN and self.drawing_new:
            # Finish new polygon
            if len(self.new_polygon) >= 3:
                pts = np.array(self.new_polygon)
                center = pts.mean(axis=0).astype(int).tolist()
                bbox = polygon_to_bbox(self.new_polygon)
                
                self.spots.append({
                    'id': len(self.spots),
                    'points': self.new_polygon.copy(),
                    'center': center,
                    'width': bbox[2] - bbox[0],
                    'height': bbox[3] - bbox[1],
                    'manual': True
                })
            
            self.new_polygon = []
            self.drawing_new = False
    
    def run(self) -> List[Dict]:
        """Run interactive review session."""
        cv2.namedWindow("Review Spots")
        cv2.setMouseCallback("Review Spots", self.mouse_callback)
        
        print("\n" + "="*60)
        print("INTERACTIVE REVIEW MODE")
        print("="*60)
        print("Controls:")
        print("  - Click spot to select")
        print("  - 'D' to delete selected spot")
        print("  - 'N' to start drawing new spot (left-click points, right-click finish)")
        print("  - 'S' to save and exit")
        print("  - 'Q' to quit without saving")
        print("="*60 + "\n")
        
        while True:
            display = self.draw()
            cv2.imshow("Review Spots", display)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == 27:
                print("Cancelled.")
                cv2.destroyWindow("Review Spots")
                return []
            
            elif key == ord('s'):
                print(f"Saving {len(self.spots)} spots...")
                cv2.destroyWindow("Review Spots")
                return self.spots
            
            elif key == ord('d') and self.selected_idx >= 0:
                print(f"Deleted spot #{self.selected_idx}")
                self.spots.pop(self.selected_idx)
                # Re-assign IDs
                for i, spot in enumerate(self.spots):
                    spot['id'] = i
                self.selected_idx = -1
            
            elif key == ord('n'):
                self.drawing_new = True
                self.new_polygon = []
                print("Drawing mode: Left-click to add points, Right-click to finish")
        
        return self.spots


# ==================== Main Entry Point ====================

def main():
    parser = argparse.ArgumentParser(
        description="Auto-segment parking spots using SAM2/FastSAM"
    )
    parser.add_argument("--source", "-s", type=str,
                       help="Video source (URL or file path)")
    parser.add_argument("--image", "-i", type=str,
                       help="Single image file path")
    parser.add_argument("--model", "-m", type=str, default="sam3",
                       choices=["sam3", "sam2", "fastsam", "auto"],
                       help="Segmentation model to use (default: sam3, 'auto' tries all)")
    parser.add_argument("--output", "-o", type=str, 
                       default="auto_segmented_zones.json",
                       help="Output JSON file path")
    parser.add_argument("--no-review", action="store_true",
                       help="Skip interactive review")
    parser.add_argument("--frame", "-f", type=int, default=90,
                       help="Frame number to extract from video (default: 90)")
    
    args = parser.parse_args()
    
    # Get input image
    if args.image:
        print(f"Loading image: {args.image}")
        image = cv2.imread(args.image)
        if image is None:
            print(f"Error: Could not load image {args.image}")
            sys.exit(1)
    elif args.source:
        print(f"Extracting frame {args.frame} from: {args.source}")
        image = extract_frame(args.source, args.frame)
        if image is None:
            print("Error: Could not extract frame from video")
            sys.exit(1)
    else:
        # Default to YouTube stream
        default_url = "https://www.youtube.com/watch?v=xufmZlIV2I8"
        print(f"No source specified, using default: {default_url}")
        image = extract_frame(default_url, args.frame)
        if image is None:
            print("Error: Could not extract frame")
            sys.exit(1)
    
    print(f"Image size: {image.shape[1]}x{image.shape[0]}")
    
    # Initialize detector
    config = SegmentConfig(output_file=args.output)
    detector = ParkingSpotDetector(model_type=args.model, config=config)
    
    # Detect spots
    print("\n" + "="*60)
    print("DETECTING PARKING SPOTS")
    print("="*60)
    
    spots = detector.detect_spots_hybrid(image, use_yolo=True)
    
    print(f"\nDetected {len(spots)} parking spots")
    
    # Interactive review
    if not args.no_review and len(spots) > 0:
        visualizer = SpotVisualizer(image, spots)
        spots = visualizer.run()
    
    # Save results
    if spots:
        with open(args.output, 'w') as f:
            json.dump(spots, f, indent=2)
        print(f"\nSaved {len(spots)} spots to {args.output}")
        
        # Also show stats
        inferred = sum(1 for s in spots if s.get('inferred', False))
        with_vehicle = sum(1 for s in spots if s.get('has_vehicle', False))
        detected = len(spots) - inferred
        
        print(f"\nBreakdown:")
        print(f"  Directly detected: {detected}")
        print(f"  Inferred/extrapolated: {inferred}")
        print(f"  With vehicles: {with_vehicle}")
    else:
        print("\nNo spots to save.")


if __name__ == "__main__":
    main()
