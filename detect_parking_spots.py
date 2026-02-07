import cv2
import numpy as np
import json
from typing import List, Dict


import cv2


class ParkingSpotDetector:
    def __init__(self, image_path):
        self.image = cv2.imread(image_path)
        self.gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        self.parking_spots = []
        
    def preprocess(self):
        """Preprocess image for better edge detection"""
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(self.gray, (5, 5), 0)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            blurred, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        return thresh
    
    def detect_spots_by_contours(self, min_area=1000, max_area=15000):
        """Detect parking spots using contour detection"""
        preprocessed = self.preprocess()
        
        # Find contours
        contours, _ = cv2.findContours(
            preprocessed, 
            cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        spot_id = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filter by area (adjust these based on your parking spot size)
            if min_area < area < max_area:
                # Approximate polygon
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Get at least 4 points
                if len(approx) >= 4:
                    # Calculate center
                    M = cv2.moments(contour)
                    if M['m00'] != 0:
                        cx = int(M['m10'] / M['m00'])
                        cy = int(M['m01'] / M['m00'])
                        
                        # Convert polygon points to list format
                        points = [[int(point[0][0]), int(point[0][1])] 
                                 for point in approx]
                        
                        spot_data = {
                            "id": spot_id,
                            "points": points,
                            "center": [cx, cy]
                        }
                        
                        self.parking_spots.append(spot_data)
                        spot_id += 1
        
        return self.parking_spots
    
    def detect_spots_by_grid(self, roi_top_left, roi_bottom_right, 
                            rows, cols, spot_width, spot_height):
        """
        Detect parking spots using grid-based approach
        Useful when spots are arranged in regular grid
        
        roi_top_left: (x, y) top-left corner of parking area
        roi_bottom_right: (x, y) bottom-right corner
        rows: number of rows
        cols: number of columns
        """
        x1, y1 = roi_top_left
        x2, y2 = roi_bottom_right
        
        # Calculate spacing
        width_step = (x2 - x1) // cols
        height_step = (y2 - y1) // rows
        
        spot_id = 0
        for row in range(rows):
            for col in range(cols):
                # Calculate spot coordinates
                x_start = x1 + col * width_step
                y_start = y1 + row * height_step
                x_end = x_start + spot_width
                y_end = y_start + spot_height
                
                # Create polygon points (rectangle)
                points = [
                    [x_start, y_start],
                    [x_end, y_start],
                    [x_end, y_end],
                    [x_start, y_end]
                ]
                
                # Calculate center
                center = [
                    (x_start + x_end) // 2,
                    (y_start + y_end) // 2
                ]
                
                spot_data = {
                    "id": spot_id,
                    "points": points,
                    "center": center
                }
                
                self.parking_spots.append(spot_data)
                spot_id += 1
        
        return self.parking_spots
    
    def visualize_spots(self, output_path='visualized_spots.jpg'):
        """Draw detected spots on image for verification"""
        vis_image = self.image.copy()
        
        for spot in self.parking_spots:
            points = np.array(spot['points'], np.int32)
            center = spot['center']
            spot_id = spot['id']
            
            # Draw polygon
            cv2.polylines(vis_image, [points], True, (0, 255, 0), 2)
            
            # Draw center point
            cv2.circle(vis_image, tuple(center), 5, (0, 0, 255), -1)
            
            # Draw ID
            cv2.putText(vis_image, str(spot_id), tuple(center), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imwrite(output_path, vis_image)
        print(f"Visualization saved to {output_path}")
        
        # Also create a resized version for easy viewing
        scale = 0.5
        resized = cv2.resize(vis_image, None, fx=scale, fy=scale)
        cv2.imwrite('visualized_spots_small.jpg', resized)
        
        return vis_image
    
    def export_to_json(self, output_path='parking_spots.json'):
        """Export parking spots to JSON format"""
        with open(output_path, 'w') as f:
            json.dump(self.parking_spots, f, indent=2)
        print(f"Exported {len(self.parking_spots)} spots to {output_path}")

# Main execution
def main():
    # Initialize detector
    detector = ParkingSpotDetector('parking_frame.jpg')
    
    # METHOD 1: Automatic contour detection
    print("Detecting spots using contour detection...")
    spots = detector.detect_spots_by_contours(min_area=1000, max_area=15000)
    
    # METHOD 2: Grid-based detection (comment out Method 1 if using this)
    # Adjust these parameters based on your parking lot layout
    # spots = detector.detect_spots_by_grid(
    #     roi_top_left=(100, 200),
    #     roi_bottom_right=(1800, 1000),
    #     rows=10,
    #     cols=20,
    #     spot_width=80,
    #     spot_height=120
    # )
    
    print(f"Detected {len(spots)} parking spots")
    
    # Visualize results
    detector.visualize_spots()
    
    # Export to JSON
    detector.export_to_json()
    
    print("\nSample output:")
    print(json.dumps(spots[:2], indent=2))

if __name__ == "__main__":
    main()
