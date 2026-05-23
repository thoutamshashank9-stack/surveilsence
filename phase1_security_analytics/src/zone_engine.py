import numpy as np
import supervision as sv
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class ZoneEngine:
    """Manages spatial zones and line-crossing logic."""
    def __init__(self, camera_id: str, zones_config: list, frame_resolution: Tuple[int, int]):
        self.camera_id = camera_id
        self.polygon_zones: Dict[str, sv.PolygonZone] = {}
        self.line_zones: Dict[str, sv.LineZone] = {}
        
        width, height = frame_resolution
        
        for zone in zones_config:
            name = zone["name"]
            zone_type = zone["type"]
            # Normalize coordinates if they were provided as percentages, 
            # otherwise assume absolute pixels. (Here we assume absolute pixels for simplicity)
            points = np.array(zone["points"], dtype=np.int32)
            
            if zone_type == "polygon":
                # PolygonZone triggers when the BOTTOM CENTER anchor of the bounding box is inside
                self.polygon_zones[name] = sv.PolygonZone(
                    polygon=points,
                    triggering_anchors=(sv.Position.BOTTOM_CENTER,)
                )
                logger.info(f"[{camera_id}] Loaded Polygon Zone: {name}")
                
            elif zone_type == "line":
                # LineZone requires exactly 2 points
                if len(points) == 2:
                    self.line_zones[name] = sv.LineZone(
                        start=sv.Point(points[0][0], points[0][1]),
                        end=sv.Point(points[1][0], points[1][1])
                    )
                    logger.info(f"[{camera_id}] Loaded Line Zone: {name}")
                else:
                    logger.error(f"Line zone '{name}' must have exactly 2 points.")

    def process_detections(self, detections: sv.Detections) -> Tuple[Dict[str, np.ndarray], Dict[str, Tuple[np.ndarray, np.ndarray]]]:
        """
        Evaluates detections against all zones.
        
        Returns:
            polygon_states: Dict mapping zone_name -> boolean mask of detections inside
            line_crossings: Dict mapping zone_name -> (crossed_in_mask, crossed_out_mask)
        """
        polygon_states = {}
        for name, zone in self.polygon_zones.items():
            # Returns a boolean array indicating which detections are in the zone
            mask = zone.trigger(detections)
            polygon_states[name] = mask
            
        line_crossings = {}
        for name, line in self.line_zones.items():
            # Updates line state and returns masks for crossing in/out
            crossed_in, crossed_out = line.trigger(detections)
            line_crossings[name] = (crossed_in, crossed_out)
            
        return polygon_states, line_crossings
