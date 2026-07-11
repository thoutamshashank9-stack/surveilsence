import time
from typing import Dict, Tuple, Optional, Any
from shapely.geometry import Point, Polygon
from app.ai.behavioral.base import BehavioralClassifierBase
from app.core.logging import get_logger

logger = get_logger(__name__)

class VelocityGatedLoiteringClassifier(BehavioralClassifierBase):
    """
    Velocity-Gated Loitering Classifier:
    Triggers alert only when target is inside the restricted zone boundary longer than
    dwell_threshold AND Exponential Moving Average ground velocity is near-stationary.
    Eliminates false alarms on fast transit pedestrian traffic.
    """
    def __init__(
        self,
        dwell_threshold_seconds: float = 30.0,
        velocity_threshold_mps: float = 0.2,
        zone_polygon: Optional[Polygon] = None
    ):
        self.dwell_threshold = dwell_threshold_seconds
        self.velocity_threshold = velocity_threshold_mps
        self.zone_polygon = zone_polygon
        
        self.dwell_starts: Dict[int, float] = {}
        self.last_update: Dict[int, float] = {}

    def update(
        self,
        track_id: int,
        centroid: Tuple[float, float],
        frame_timestamp: float,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Expects kwargs:
            ema_velocity: float (EMA velocity calculated on homography world coords)
        """
        self.last_update[track_id] = frame_timestamp
        ema_velocity = kwargs.get("ema_velocity", 0.0)

        # If centroid zone check is active
        if self.zone_polygon:
            point = Point(centroid)
            in_zone = point.within(self.zone_polygon)
        else:
            in_zone = True

        if not in_zone:
            self.dwell_starts.pop(track_id, None)
            return None

        # Track entry timestamp
        if track_id not in self.dwell_starts:
            self.dwell_starts[track_id] = frame_timestamp
            return None

        # Compute cumulative dwell time
        dwell_time = frame_timestamp - self.dwell_starts[track_id]

        # Trigger loitering alarm if loitering duration is exceeded AND velocity is near-stationary
        if dwell_time >= self.dwell_threshold and ema_velocity <= self.velocity_threshold:
            logger.warn("Velocity-Gated Loitering Alarm!", track_id=track_id, dwell=dwell_time, vel=ema_velocity)
            return {
                "event": "VELOCITY_LOITERING",
                "track_id": track_id,
                "timestamp": frame_timestamp,
                "description": f"Target P{track_id} loitering in zone (dwell: {int(dwell_time)}s, velocity: {ema_velocity:.2f}m/s)."
            }

        return None

    def reset(self) -> None:
        self.dwell_starts.clear()
        self.last_update.clear()

    def cleanup(self, max_age_seconds: float = 60.0) -> None:
        curr_time = time.time()
        for track_id, last_ts in list(self.last_update.items()):
            if curr_time - last_ts > max_age_seconds:
                self.dwell_starts.pop(track_id, None)
                self.last_update.pop(track_id, None)
