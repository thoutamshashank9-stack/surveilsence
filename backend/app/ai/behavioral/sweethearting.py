import time
from typing import Dict, List, Tuple, Optional, Any
from shapely.geometry import Point, Polygon
from app.ai.behavioral.base import BehavioralClassifierBase
from app.core.logging import get_logger

logger = get_logger(__name__)

class SweetheartingClassifier(BehavioralClassifierBase):
    """
    Cashier sweethearting detection logic:
    Detects when an item moves from the conveyor zone to the bagging zone without 
    a corresponding POS transaction log scan event registered within a time window.
    """
    def __init__(
        self,
        conveyor_poly: Polygon,
        bagging_poly: Polygon,
        time_threshold: float = 3.0
    ):
        self.conveyor_poly = conveyor_poly
        self.bagging_poly = bagging_poly
        self.time_threshold = time_threshold
        
        # TrackID -> state dict: {"in_conveyor": bool, "crossed_to_bagging": bool, "t_cross": float}
        self.active_tracks: Dict[int, Dict[str, Any]] = {}
        
        # Buffer of scans: list of (timestamp, upc)
        self.pos_scans: List[Tuple[float, str]] = []
        self.last_update: Dict[int, float] = {}

    def register_pos_scan(self, timestamp: float, upc: str) -> None:
        """
        Register a barcode read from the POS cash register stream.
        """
        self.pos_scans.append((timestamp, upc))
        # Garbage collect scans older than 60 seconds
        curr_time = time.time()
        self.pos_scans = [s for s in self.pos_scans if curr_time - s[0] < 60.0]
        logger.debug("POS scan registered in buffer", timestamp=timestamp, upc=upc)

    def update(
        self,
        track_id: int,
        centroid: Tuple[float, float],
        frame_timestamp: float,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        self.last_update[track_id] = frame_timestamp
        point = Point(centroid)

        if track_id not in self.active_tracks:
            self.active_tracks[track_id] = {
                "in_conveyor": False,
                "crossed_to_bagging": False,
                "t_cross": None
            }

        track_state = self.active_tracks[track_id]

        # 1. Track entry to conveyor zone
        if point.within(self.conveyor_poly):
            track_state["in_conveyor"] = True

        # 2. Track transition to bagging zone
        if (
            track_state["in_conveyor"] 
            and point.within(self.bagging_poly) 
            and not track_state["crossed_to_bagging"]
        ):
            track_state["crossed_to_bagging"] = True
            track_state["t_cross"] = frame_timestamp
            
            # Cross-reference with the POS scan history log
            matched_scan = False
            for scan_time, upc in self.pos_scans:
                if abs(frame_timestamp - scan_time) <= self.time_threshold:
                    matched_scan = True
                    break

            if not matched_scan:
                logger.warn("Cashier Sweethearting Anomaly Detected!", track_id=track_id)
                return {
                    "event": "SWEETHEARTING_DETECTION",
                    "track_id": track_id,
                    "timestamp": frame_timestamp,
                    "description": f"Item P{track_id} moved from conveyor to bagging zone without checkout scan."
                }

        return None

    def reset(self) -> None:
        self.active_tracks.clear()
        self.pos_scans.clear()
        self.last_update.clear()

    def cleanup(self, max_age_seconds: float = 60.0) -> None:
        curr_time = time.time()
        for track_id, last_ts in list(self.last_update.items()):
            if curr_time - last_ts > max_age_seconds:
                self.active_tracks.pop(track_id, None)
                self.last_update.pop(track_id, None)
