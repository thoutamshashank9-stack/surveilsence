from typing import Dict, List, Set, Tuple, Optional, Any
from shapely.geometry import Point, Polygon, LineString
import supervision as sv
import numpy as np

class ZoneEngine:
    def __init__(self, camera_zones_config: List[Any]):
        self.polygons: Dict[str, Polygon] = {}
        self.lines: Dict[str, LineString] = {}
        self.zone_metadata: Dict[str, Dict[str, Any]] = {}
        
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

            if z_type == "polygon":
                if len(points) >= 3:
                    self.polygons[name] = Polygon(points)
            elif z_type == "line":
                if len(points) == 2:
                    self.lines[name] = LineString(points)

    def evaluate_zones(
        self,
        detections: sv.Detections
    ) -> Dict[str, Set[int]]:
        """
        Evaluate polygon zone occupancy.
        Returns:
            Dict[str, Set[int]]: Map of zone_name -> set of track_ids inside.
        """
        zone_states: Dict[str, Set[int]] = {name: set() for name in self.polygons.keys()}
        
        if detections.tracker_id is None or len(detections) == 0:
            return zone_states

        for idx, bbox in enumerate(detections.xyxy):
            track_id = int(detections.tracker_id[idx])
            
            # Bottom center anchor is best for zone calculations (feet position)
            bx = (bbox[0] + bbox[2]) / 2
            by = bbox[3]  # bottom
            
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
        Check if a track crossed any line zone.
        Returns:
            List[Tuple[str, str]]: List of (line_name, direction) crossings.
        """
        crossings = []
        movement_line = LineString([prev_pos, curr_pos])
        
        for name, line in self.lines.items():
            if line.intersects(movement_line):
                # Calculate crossing direction
                direction = self._calculate_crossing_direction(line, prev_pos, curr_pos)
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
