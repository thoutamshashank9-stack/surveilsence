from typing import Dict, List, Set, Tuple, Optional, Any
from shapely.geometry import Point, Polygon, LineString
import supervision as sv
import numpy as np

from app.ai.postprocessing.homography import HomographyCalibrator

class ZoneEngine:
    def __init__(self, camera_zones_config: List[Any], homography: Optional[HomographyCalibrator] = None):
        self.polygons: Dict[str, Polygon] = {}
        self.lines: Dict[str, LineString] = {}
        self.zone_metadata: Dict[str, Dict[str, Any]] = {}
        self.homography = homography
        
        self._load_zones(camera_zones_config)

    def _load_zones(self, config: List[Any]) -> None:
        for z in config:
            name = z.name if hasattr(z, "name") else z.get("name")
            z_type = z.type if hasattr(z, "type") else z.get("type")
            points = z.points if hasattr(z, "points") else z.get("points")
            restricted = z.restricted if hasattr(z, "restricted") else z.get("restricted", False)
            direction = z.direction if hasattr(z, "direction") else z.get("direction", None)

            # Store metadata
            self.zone_metadata[name] = {
                "type": z_type,
                "restricted": restricted,
                "direction": direction
            }

            # Map points to ground-plane meters if homography calibration is active
            if self.homography and self.homography.is_calibrated():
                transformed_points = [self.homography.pixel_to_world(p[0], p[1]) for p in points]
            else:
                transformed_points = points

            if z_type == "polygon":
                if len(transformed_points) >= 3:
                    self.polygons[name] = Polygon(transformed_points)
            elif z_type == "line":
                if len(transformed_points) == 2:
                    self.lines[name] = LineString(transformed_points)

    def evaluate_zones(
        self,
        detections: sv.Detections
    ) -> Dict[str, Set[int]]:
        """
        Evaluate polygon zone occupancy in homography-corrected meter space (if calibrated).
        """
        zone_states: Dict[str, Set[int]] = {name: set() for name in self.polygons.keys()}
        
        if detections.tracker_id is None or len(detections) == 0:
            return zone_states

        for idx, bbox in enumerate(detections.xyxy):
            track_id = int(detections.tracker_id[idx])
            
            # Bottom center anchor is best for zone calculations (feet position)
            bx = (bbox[0] + bbox[2]) / 2
            by = bbox[3]  # bottom
            
            if self.homography and self.homography.is_calibrated():
                wx, wy = self.homography.pixel_to_world(bx, by)
                point = Point(wx, wy)
            else:
                point = Point(bx, by)
            
            for zone_name, poly in self.polygons.items():
                if poly.contains(point):
                    zone_states[zone_name].add(track_id)
                    
        return zone_states

    def check_line_crossings(
        self,
        track_id: int,
        prev_pos: Tuple[float, float],
        curr_pos: Tuple[float, float]
    ) -> List[Tuple[str, str]]:
        """
        Check if a track crossed any line zone, transformed via homography (if calibrated).
        """
        crossings = []
        
        if self.homography and self.homography.is_calibrated():
            w_prev = self.homography.pixel_to_world(prev_pos[0], prev_pos[1])
            w_curr = self.homography.pixel_to_world(curr_pos[0], curr_pos[1])
        else:
            w_prev = prev_pos
            w_curr = curr_pos

        movement_line = LineString([w_prev, w_curr])
        
        for name, line in self.lines.items():
            if line.intersects(movement_line):
                # Calculate crossing direction
                direction = self._calculate_crossing_direction(line, w_prev, w_curr)
                crossings.append((name, direction))
                
        return crossings

    def _calculate_crossing_direction(
        self,
        line: LineString,
        p1: Tuple[float, float],
        p2: Tuple[float, float]
    ) -> str:
        """
        Determine direction of crossing.
        For a line from L1 to L2, checking if vector P1->P2 crossed left-to-right or right-to-left.
        """
        l1 = line.coords[0]
        l2 = line.coords[1]
        
        # Line vector
        lx = l2[0] - l1[0]
        ly = l2[1] - l1[1]
        
        # Movement vector
        mx = p2[0] - p1[0]
        my = p2[1] - p1[1]
        
        # Cross product to determine side
        cross_product = (p2[0] - l1[0]) * ly - (p2[1] - l1[1]) * lx
        
        # Simplified: depending on side, return 'in' or 'out'
        if cross_product > 0:
            return "in"
        else:
            return "out"

