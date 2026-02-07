"""
Parking Spot Detection using SAM3 (Segment Anything Model 3)

This script uses Meta's SAM3 model to detect and segment INDIVIDUAL parking spots
in an aerial parking lot image using a tiled/zoom approach for high accuracy.

Features:
- Tiled processing for high-resolution images (zoom into regions)
- Dense point grid sampling for individual spot detection
- Strict area filtering for small parking spots
- Non-maximum suppression to remove duplicates

Usage:
    python detect_parking_spots_sam3.py --input parking_frame.jpg --output parking_zones.json
    python detect_parking_spots_sam3.py -i parking_frame.jpg -o zones.json --tiles 4 --method tiled
"""

import argparse
import json
import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict
from dataclasses import dataclass


@dataclass
class SpotCandidate:
    """Represents a potential parking spot detection."""
    mask: np.ndarray
    area: int
    center: Tuple[int, int]
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    confidence: float = 1.0


def install_dependencies():
    """Install required packages if not present."""
    import subprocess
    import sys
    
    packages = ['ultralytics>=8.3.237', 'opencv-python', 'numpy']
    for package in packages:
        try:
            __import__(package.split('>=')[0].replace('-', '_'))
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])


def get_polygon_from_mask(mask: np.ndarray, simplify_epsilon: float = 2.0) -> list:
    """
    Extract polygon points from a binary mask.
    
    Args:
        mask: Binary mask array
        simplify_epsilon: Epsilon for polygon simplification (higher = simpler)
    
    Returns:
        List of [x, y] points forming the polygon
    """
    # Ensure mask is uint8
    if mask.dtype != np.uint8:
        mask = (mask * 255).astype(np.uint8)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return []
    
    # Get the largest contour
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Simplify the polygon
    epsilon = simplify_epsilon * cv2.arcLength(largest_contour, True) / 100
    approx = cv2.approxPolyDP(largest_contour, epsilon, True)
    
    # Convert to list of [x, y] points
    points = [[int(point[0][0]), int(point[0][1])] for point in approx]
    
    return points


def get_mask_center(mask: np.ndarray) -> list:
    """
    Calculate the centroid of a binary mask.
    
    Args:
        mask: Binary mask array
    
    Returns:
        [x, y] center coordinates
    """
    if mask.dtype != np.uint8:
        mask = (mask * 255).astype(np.uint8)
    
    moments = cv2.moments(mask)
    if moments['m00'] == 0:
        # Fallback to mask center if moments fail
        ys, xs = np.where(mask > 0)
        if len(xs) == 0:
            return [0, 0]
        return [int(np.mean(xs)), int(np.mean(ys))]
    
    cx = int(moments['m10'] / moments['m00'])
    cy = int(moments['m01'] / moments['m00'])
    return [cx, cy]


def estimate_spot_size(image_shape: tuple) -> Tuple[int, int]:
    """
    Estimate typical parking spot size based on image dimensions.
    For aerial parking lot images, spots are typically small relative to image.
    
    Returns:
        (min_area, max_area) tuple
    """
    total_pixels = image_shape[0] * image_shape[1]
    
    # Parking spots in aerial view are typically 0.01% - 0.3% of image
    min_area = max(200, int(total_pixels * 0.0001))
    max_area = min(15000, int(total_pixels * 0.003))
    
    return min_area, max_area


def filter_parking_spots(masks: list, image_shape: tuple, 
                         min_area: int = None, max_area: int = None,
                         min_aspect_ratio: float = 1.0, max_aspect_ratio: float = 4.0,
                         min_solidity: float = 0.5) -> List[SpotCandidate]:
    """
    Filter detected masks to keep only valid individual parking spots.
    Uses strict filtering for small, rectangular parking spots.
    
    Args:
        masks: List of binary mask arrays
        image_shape: Shape of the original image (height, width)
        min_area: Minimum area (auto-estimated if None)
        max_area: Maximum area (auto-estimated if None)
        min_aspect_ratio: Minimum width/height ratio
        max_aspect_ratio: Maximum width/height ratio (parking spots are roughly 1:2 to 1:3)
        min_solidity: Minimum solidity (area / convex hull area)
    
    Returns:
        List of SpotCandidate objects
    """
    # Auto-estimate size constraints if not provided
    if min_area is None or max_area is None:
        est_min, est_max = estimate_spot_size(image_shape)
        min_area = min_area or est_min
        max_area = max_area or est_max
    
    valid_candidates = []
    
    for i, mask in enumerate(masks):
        if mask.dtype != np.uint8:
            mask_uint8 = (mask * 255).astype(np.uint8)
        else:
            mask_uint8 = mask
        
        # Calculate area
        area = cv2.countNonZero(mask_uint8)
        
        # Strict area filtering - reject if too big or too small
        if area < min_area or area > max_area:
            continue
        
        # Get bounding rect for aspect ratio
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        
        largest_contour = max(contours, key=cv2.contourArea)
        contour_area = cv2.contourArea(largest_contour)
        
        if contour_area < min_area:
            continue
        
        # Check solidity (how "filled" the shape is)
        hull = cv2.convexHull(largest_contour)
        hull_area = cv2.contourArea(hull)
        if hull_area > 0:
            solidity = contour_area / hull_area
            if solidity < min_solidity:
                continue
        
        # Get rotated bounding rect
        rect = cv2.minAreaRect(largest_contour)
        width, height = rect[1]
        
        if height == 0 or width == 0:
            continue
        
        aspect_ratio = max(width, height) / min(width, height)
        
        # Parking spots typically have aspect ratio between 1.2 and 3.5
        if aspect_ratio < min_aspect_ratio or aspect_ratio > max_aspect_ratio:
            continue
        
        # Get bounding box
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Calculate center
        M = cv2.moments(mask_uint8)
        if M['m00'] != 0:
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
        else:
            cx, cy = x + w // 2, y + h // 2
        
        candidate = SpotCandidate(
            mask=mask,
            area=area,
            center=(cx, cy),
            bbox=(x, y, w, h)
        )
        valid_candidates.append(candidate)
    
    return valid_candidates


def non_maximum_suppression(candidates: List[SpotCandidate], 
                           iou_threshold: float = 0.3,
                           distance_threshold: int = 30) -> List[SpotCandidate]:
    """
    Remove overlapping detections, keeping the best ones.
    
    Args:
        candidates: List of SpotCandidate objects
        iou_threshold: IoU threshold for considering overlap
        distance_threshold: Minimum center distance in pixels
    
    Returns:
        Filtered list of candidates
    """
    if not candidates:
        return []
    
    # Sort by area (prefer medium-sized spots)
    candidates = sorted(candidates, key=lambda c: c.area, reverse=True)
    
    keep = []
    
    for candidate in candidates:
        should_keep = True
        
        for kept in keep:
            # Check center distance
            dist = np.sqrt(
                (candidate.center[0] - kept.center[0])**2 + 
                (candidate.center[1] - kept.center[1])**2
            )
            
            if dist < distance_threshold:
                should_keep = False
                break
            
            # Check IoU
            if candidate.mask.shape == kept.mask.shape:
                intersection = np.logical_and(candidate.mask > 0, kept.mask > 0).sum()
                union = np.logical_or(candidate.mask > 0, kept.mask > 0).sum()
                
                if union > 0:
                    iou = intersection / union
                    if iou > iou_threshold:
                        should_keep = False
                        break
        
        if should_keep:
            keep.append(candidate)
    
    return keep


def detect_parking_spots_tiled(image_path: str,
                                num_tiles: int = 4,
                                overlap: float = 0.2,
                                points_per_tile: int = 100,
                                conf_threshold: float = 0.25,
                                output_visualization: str = None) -> list:
    """
    Detect individual parking spots using tiled/zoom approach with dense point sampling.
    This method processes the image in smaller tiles for higher accuracy on small spots.
    
    Args:
        image_path: Path to the input image
        num_tiles: Number of tiles per dimension (e.g., 4 = 4x4 = 16 tiles)
        overlap: Overlap ratio between tiles (0.2 = 20% overlap)
        points_per_tile: Number of point samples per tile
        conf_threshold: Confidence threshold
        output_visualization: Path to save visualization
    
    Returns:
        List of parking spot dictionaries
    """
    from ultralytics.models.sam import SAM3Predictor
    
    print(f"Loading image: {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    height, width = image.shape[:2]
    print(f"Image size: {width}x{height}")
    
    # Calculate tile dimensions with overlap
    tile_h = int(height / num_tiles * (1 + overlap))
    tile_w = int(width / num_tiles * (1 + overlap))
    step_h = height // num_tiles
    step_w = width // num_tiles
    
    # Initialize SAM3 predictor
    overrides = dict(
        conf=conf_threshold,
        task="segment",
        mode="predict",
        model="sam3.pt",
        half=True,
        save=False,
        verbose=False,
    )
    
    print("Initializing SAM3 predictor...")
    predictor = SAM3Predictor(overrides=overrides)
    
    all_candidates = []
    total_tiles = num_tiles * num_tiles
    
    print(f"Processing {total_tiles} tiles ({num_tiles}x{num_tiles})...")
    
    # Process each tile
    tile_idx = 0
    for row in range(num_tiles):
        for col in range(num_tiles):
            tile_idx += 1
            
            # Calculate tile boundaries
            y_start = max(0, row * step_h - int(step_h * overlap / 2))
            y_end = min(height, y_start + tile_h)
            x_start = max(0, col * step_w - int(step_w * overlap / 2))
            x_end = min(width, x_start + tile_w)
            
            # Extract tile
            tile = image[y_start:y_end, x_start:x_end]
            tile_height, tile_width = tile.shape[:2]
            
            if tile_height < 50 or tile_width < 50:
                continue
            
            print(f"  Tile {tile_idx}/{total_tiles}: ({x_start},{y_start}) -> ({x_end},{y_end})")
            
            # Save tile temporarily for SAM3
            tile_path = f"/tmp/tile_{tile_idx}.jpg"
            cv2.imwrite(tile_path, tile)
            
            try:
                predictor.set_image(tile_path)
                
                # Generate dense point grid within tile
                points_per_dim = int(np.sqrt(points_per_tile))
                x_step = tile_width // (points_per_dim + 1)
                y_step = tile_height // (points_per_dim + 1)
                
                tile_masks = []
                
                for py in range(1, points_per_dim + 1):
                    for px in range(1, points_per_dim + 1):
                        point_x = px * x_step
                        point_y = py * y_step
                        
                        try:
                            results = predictor(points=[[point_x, point_y]], labels=[1])
                            for result in results:
                                if result.masks is not None:
                                    masks = result.masks.data.cpu().numpy()
                                    for mask in masks:
                                        tile_masks.append(mask)
                        except:
                            continue
                
                print(f"    Found {len(tile_masks)} raw masks in tile")
                
                # Filter valid spots within this tile
                candidates = filter_parking_spots(
                    tile_masks,
                    (tile_height, tile_width),
                    min_aspect_ratio=1.2,
                    max_aspect_ratio=4.0,
                    min_solidity=0.6
                )
                
                # Transform coordinates back to full image
                for candidate in candidates:
                    # Offset the center
                    candidate.center = (
                        candidate.center[0] + x_start,
                        candidate.center[1] + y_start
                    )
                    # Offset the bbox
                    candidate.bbox = (
                        candidate.bbox[0] + x_start,
                        candidate.bbox[1] + y_start,
                        candidate.bbox[2],
                        candidate.bbox[3]
                    )
                    # Create full-size mask
                    full_mask = np.zeros((height, width), dtype=candidate.mask.dtype)
                    mask_h, mask_w = candidate.mask.shape[:2]
                    y_end_m = min(y_start + mask_h, height)
                    x_end_m = min(x_start + mask_w, width)
                    full_mask[y_start:y_end_m, x_start:x_end_m] = candidate.mask[:y_end_m-y_start, :x_end_m-x_start]
                    candidate.mask = full_mask
                    
                    all_candidates.append(candidate)
                
                print(f"    Kept {len(candidates)} valid spots")
                
            except Exception as e:
                print(f"    Error processing tile: {e}")
                continue
            
            # Clean up temp file
            Path(tile_path).unlink(missing_ok=True)
    
    print(f"\nTotal candidates before NMS: {len(all_candidates)}")
    
    # Apply non-maximum suppression
    final_candidates = non_maximum_suppression(
        all_candidates, 
        iou_threshold=0.3,
        distance_threshold=25
    )
    
    print(f"After NMS: {len(final_candidates)} spots")
    
    # Convert to output format
    parking_spots = []
    for idx, candidate in enumerate(final_candidates):
        points = get_polygon_from_mask(candidate.mask)
        if len(points) < 3:
            continue
        
        parking_spots.append({
            "id": idx,
            "points": points,
            "center": list(candidate.center)
        })
    
    # Re-number IDs
    for i, spot in enumerate(parking_spots):
        spot["id"] = i
    
    if output_visualization:
        visualize_spots(image, parking_spots, output_visualization)
    
    return parking_spots


def detect_parking_spots_sam3(image_path: str, 
                               text_prompts: list = None,
                               conf_threshold: float = 0.25,
                               output_visualization: str = None) -> list:
    """
    Detect parking spots using SAM3 with text prompts.
    Note: This may detect large areas. Use tiled method for individual spots.
    
    Args:
        image_path: Path to the input image
        text_prompts: List of text prompts to identify parking spots
        conf_threshold: Confidence threshold for detection
        output_visualization: Path to save visualization (optional)
    
    Returns:
        List of parking spot dictionaries with id, points, and center
    """
    from ultralytics.models.sam import SAM3SemanticPredictor
    
    if text_prompts is None:
        # More specific prompts for individual spots
        text_prompts = [
            "single parking spot",
            "individual parking bay",
            "one parking space",
            "empty parking stall",
            "parked car space"
        ]
    
    # Initialize SAM3 predictor
    overrides = dict(
        conf=conf_threshold,
        task="segment",
        mode="predict",
        model="sam3.pt",
        half=True,
        save=False,
        verbose=False,
    )
    
    print("Initializing SAM3 predictor...")
    predictor = SAM3SemanticPredictor(overrides=overrides)
    
    print(f"Loading image: {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    predictor.set_image(image_path)
    
    print(f"Running SAM3 segmentation with prompts: {text_prompts}")
    results = predictor(text=text_prompts)
    
    all_masks = []
    
    for result in results:
        if result.masks is None:
            continue
        masks = result.masks.data.cpu().numpy()
        for mask in masks:
            all_masks.append(mask)
    
    print(f"Found {len(all_masks)} raw segments")
    
    # Filter with strict constraints
    candidates = filter_parking_spots(
        all_masks, 
        image.shape[:2],
        min_aspect_ratio=1.2,
        max_aspect_ratio=4.0,
        min_solidity=0.6
    )
    
    # Apply NMS
    candidates = non_maximum_suppression(candidates, iou_threshold=0.3, distance_threshold=25)
    
    print(f"Filtered to {len(candidates)} valid parking spots")
    
    # Convert to output format
    parking_spots = []
    for idx, candidate in enumerate(candidates):
        points = get_polygon_from_mask(candidate.mask)
        if len(points) < 3:
            continue
        
        parking_spots.append({
            "id": idx,
            "points": points,
            "center": list(candidate.center)
        })
    
    for i, spot in enumerate(parking_spots):
        spot["id"] = i
    
    if output_visualization:
        visualize_spots(image, parking_spots, output_visualization)
    
    return parking_spots


def detect_parking_spots_dense_grid(image_path: str,
                                     grid_density: int = 30,
                                     conf_threshold: float = 0.25,
                                     output_visualization: str = None) -> list:
    """
    Detection using very dense point grid sampling across the entire image.
    Uses strict filtering to keep only individual parking spots.
    
    Args:
        image_path: Path to the input image
        grid_density: Number of sample points per dimension
        conf_threshold: Confidence threshold
        output_visualization: Path to save visualization
    
    Returns:
        List of parking spot dictionaries
    """
    from ultralytics.models.sam import SAM3Predictor
    
    overrides = dict(
        conf=conf_threshold,
        task="segment",
        mode="predict",
        model="sam3.pt",
        half=True,
        save=False,
        verbose=False,
    )
    
    print("Initializing SAM3 predictor for dense grid detection...")
    predictor = SAM3Predictor(overrides=overrides)
    
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    height, width = image.shape[:2]
    predictor.set_image(image_path)
    
    # Focus on parking lot area (adjust based on your image)
    x_start, x_end = int(width * 0.02), int(width * 0.98)
    y_start, y_end = int(height * 0.35), int(height * 0.98)
    
    x_step = max(1, (x_end - x_start) // grid_density)
    y_step = max(1, (y_end - y_start) // grid_density)
    
    all_masks = []
    total_points = ((x_end - x_start) // x_step) * ((y_end - y_start) // y_step)
    
    print(f"Sampling {total_points} points across parking area...")
    
    point_count = 0
    for x in range(x_start, x_end, x_step):
        for y in range(y_start, y_end, y_step):
            point_count += 1
            if point_count % 100 == 0:
                print(f"  Progress: {point_count}/{total_points} points...")
            
            try:
                results = predictor(points=[[x, y]], labels=[1])
                for result in results:
                    if result.masks is not None:
                        masks = result.masks.data.cpu().numpy()
                        for mask in masks:
                            all_masks.append(mask)
            except:
                continue
    
    print(f"Collected {len(all_masks)} raw segments")
    
    # Filter with strict constraints
    candidates = filter_parking_spots(
        all_masks,
        image.shape[:2],
        min_aspect_ratio=1.2,
        max_aspect_ratio=4.0,
        min_solidity=0.6
    )
    
    print(f"After filtering: {len(candidates)} candidates")
    
    # Apply NMS
    final_candidates = non_maximum_suppression(
        candidates, 
        iou_threshold=0.3,
        distance_threshold=25
    )
    
    print(f"After NMS: {len(final_candidates)} spots")
    
    parking_spots = []
    for idx, candidate in enumerate(final_candidates):
        points = get_polygon_from_mask(candidate.mask)
        if len(points) < 3:
            continue
        
        parking_spots.append({
            "id": idx,
            "points": points,
            "center": list(candidate.center)
        })
    
    for i, spot in enumerate(parking_spots):
        spot["id"] = i
    
    if output_visualization:
        visualize_spots(image, parking_spots, output_visualization)
    
    return parking_spots


def remove_duplicate_masks(masks: list, iou_threshold: float = 0.5) -> list:
    """
    Remove duplicate/overlapping masks based on IoU.
    
    Args:
        masks: List of binary mask arrays
        iou_threshold: IoU threshold above which masks are considered duplicates
    
    Returns:
        List of unique masks
    """
    if not masks:
        return []
    
    unique_masks = [masks[0]]
    
    for mask in masks[1:]:
        is_duplicate = False
        for unique_mask in unique_masks:
            # Calculate IoU
            intersection = np.logical_and(mask > 0, unique_mask > 0).sum()
            union = np.logical_or(mask > 0, unique_mask > 0).sum()
            
            if union == 0:
                continue
            
            iou = intersection / union
            if iou > iou_threshold:
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_masks.append(mask)
    
    return unique_masks


def visualize_spots_detailed(image: np.ndarray, parking_spots: list, output_path: str):
    """
    Create detailed visualization with zoom regions.
    
    Args:
        image: Original image
        parking_spots: List of parking spot dictionaries
        output_path: Path to save visualization
    """
    vis_image = image.copy()
    
    # Use a consistent green color for all spots
    spot_color = (0, 255, 0)
    
    for spot in parking_spots:
        points = np.array(spot['points'], np.int32)
        center = spot['center']
        spot_id = spot['id']
        
        # Draw polygon outline (thin line)
        cv2.polylines(vis_image, [points], True, spot_color, 1)
        
        # Draw center point (small)
        cv2.circle(vis_image, tuple(center), 3, (0, 0, 255), -1)
        
        # Draw ID label (small font)
        cv2.putText(vis_image, str(spot_id), (center[0] - 5, center[1] + 3),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
    
    cv2.imwrite(output_path, vis_image)
    print(f"Visualization saved to {output_path}")
    
    # Save smaller version
    scale = 0.5
    resized = cv2.resize(vis_image, None, fx=scale, fy=scale)
    small_path = output_path.replace('.jpg', '_small.jpg').replace('.png', '_small.png')
    cv2.imwrite(small_path, resized)
    
    # Create zoomed detail views
    height, width = image.shape[:2]
    
    # Create a 2x2 grid of zoomed sections
    zoom_regions = [
        (0, 0, width//2, height//2, "top_left"),
        (width//2, 0, width, height//2, "top_right"),
        (0, height//2, width//2, height, "bottom_left"),
        (width//2, height//2, width, height, "bottom_right"),
    ]
    
    for x1, y1, x2, y2, name in zoom_regions:
        region = vis_image[y1:y2, x1:x2]
        # Scale up 2x for detail
        zoomed = cv2.resize(region, None, fx=2, fy=2)
        zoom_path = output_path.replace('.jpg', f'_zoom_{name}.jpg').replace('.png', f'_zoom_{name}.png')
        cv2.imwrite(zoom_path, zoomed)
        print(f"Zoom region saved to {zoom_path}")


def visualize_spots(image: np.ndarray, parking_spots: list, output_path: str):
    """
    Visualize detected parking spots on the image.
    
    Args:
        image: Original image
        parking_spots: List of parking spot dictionaries
        output_path: Path to save visualization
    """
    vis_image = image.copy()
    
    # Generate distinct colors for each spot
    np.random.seed(42)
    colors = [(np.random.randint(0, 255), np.random.randint(0, 255), np.random.randint(0, 255)) 
              for _ in range(len(parking_spots))]
    
    for spot, color in zip(parking_spots, colors):
        points = np.array(spot['points'], np.int32)
        center = spot['center']
        spot_id = spot['id']
        
        # Draw filled polygon with transparency
        overlay = vis_image.copy()
        cv2.fillPoly(overlay, [points], color)
        cv2.addWeighted(overlay, 0.3, vis_image, 0.7, 0, vis_image)
        
        # Draw polygon outline
        cv2.polylines(vis_image, [points], True, (0, 255, 0), 2)
        
        # Draw center point
        cv2.circle(vis_image, tuple(center), 5, (0, 0, 255), -1)
        
        # Draw ID label
        cv2.putText(vis_image, str(spot_id), (center[0] - 10, center[1] + 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    
    cv2.imwrite(output_path, vis_image)
    print(f"Visualization saved to {output_path}")
    
    # Also save a smaller version
    scale = 0.5
    resized = cv2.resize(vis_image, None, fx=scale, fy=scale)
    small_path = output_path.replace('.jpg', '_small.jpg').replace('.png', '_small.png')
    cv2.imwrite(small_path, resized)
    print(f"Small visualization saved to {small_path}")


def export_to_json(parking_spots: list, output_path: str):
    """
    Export parking spots to JSON file.
    
    Args:
        parking_spots: List of parking spot dictionaries
        output_path: Output JSON file path
    """
    with open(output_path, 'w') as f:
        json.dump(parking_spots, f, indent=2)
    print(f"Exported {len(parking_spots)} parking spots to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Detect individual parking spots using SAM3 (Segment Anything Model 3)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Recommended: Tiled approach for best accuracy on individual spots
  python detect_parking_spots_sam3.py -i parking_frame.jpg -m tiled --tiles 5
  
  # Dense grid sampling (slower but thorough)
  python detect_parking_spots_sam3.py -i parking_frame.jpg -m grid --density 40
  
  # Text-based detection (may detect larger areas)
  python detect_parking_spots_sam3.py -i parking_frame.jpg -m text
        """
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='parking_frame.jpg',
        help='Input image path'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='sam3_parking_zones.json',
        help='Output JSON file path'
    )
    parser.add_argument(
        '--visualization', '-v',
        type=str,
        default='sam3_visualized_spots.jpg',
        help='Visualization output path'
    )
    parser.add_argument(
        '--method', '-m',
        type=str,
        choices=['text', 'grid', 'tiled'],
        default='tiled',
        help='Detection method: tiled (recommended), grid, or text'
    )
    parser.add_argument(
        '--tiles',
        type=int,
        default=5,
        help='Number of tiles per dimension for tiled method (e.g., 5 = 5x5 grid)'
    )
    parser.add_argument(
        '--density',
        type=int,
        default=30,
        help='Grid density for grid method'
    )
    parser.add_argument(
        '--confidence', '-c',
        type=float,
        default=0.25,
        help='Confidence threshold'
    )
    parser.add_argument(
        '--prompts', '-p',
        type=str,
        nargs='+',
        default=None,
        help='Custom text prompts for text method'
    )
    parser.add_argument(
        '--detailed-viz',
        action='store_true',
        help='Generate detailed visualization with zoom regions'
    )
    
    args = parser.parse_args()
    
    # Verify input exists
    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}")
        return
    
    print(f"SAM3 Parking Spot Detection - Individual Spot Mode")
    print(f"=" * 50)
    print(f"Input: {args.input}")
    print(f"Method: {args.method}")
    print(f"Confidence: {args.confidence}")
    
    # Run detection based on method
    if args.method == 'tiled':
        print(f"Tiles: {args.tiles}x{args.tiles}")
        parking_spots = detect_parking_spots_tiled(
            image_path=args.input,
            num_tiles=args.tiles,
            conf_threshold=args.confidence,
            output_visualization=args.visualization
        )
    elif args.method == 'grid':
        print(f"Grid density: {args.density}")
        parking_spots = detect_parking_spots_dense_grid(
            image_path=args.input,
            grid_density=args.density,
            conf_threshold=args.confidence,
            output_visualization=args.visualization
        )
    else:  # text
        parking_spots = detect_parking_spots_sam3(
            image_path=args.input,
            text_prompts=args.prompts,
            conf_threshold=args.confidence,
            output_visualization=args.visualization
        )
    
    # Generate detailed visualization if requested
    if args.detailed_viz and parking_spots:
        image = cv2.imread(args.input)
        visualize_spots_detailed(image, parking_spots, args.visualization)
    
    # Export results
    export_to_json(parking_spots, args.output)
    
    print(f"\n{'=' * 50}")
    print(f"Detection complete!")
    print(f"Found {len(parking_spots)} individual parking spots")
    print(f"Output: {args.output}")
    print(f"Visualization: {args.visualization}")
    
    if parking_spots:
        print(f"\nSample output (first 2 spots):")
        print(json.dumps(parking_spots[:2], indent=2))


if __name__ == "__main__":
    main()
