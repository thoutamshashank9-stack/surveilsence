import time
import math
from typing import Dict, List, Tuple, Optional, Any
from shapely.geometry import Point, Polygon
from app.ai.behavioral.base import BehavioralClassifierBase
from app.core.logging import get_logger

logger = get_logger(__name__)

class UnusualActivityState:
    def __init__(self, track_id: int, timestamp: float, bbox: Optional[Tuple[float, float, float, float]] = None):
        self.track_id = track_id
        self.last_ts = timestamp
        self.consecutive_fast_count = 0
        self.initial_aspect_ratio: float = 1.0
        if bbox is not None:
            w = max(1.0, bbox[2] - bbox[0])
            h = max(1.0, bbox[3] - bbox[1])
            self.initial_aspect_ratio = h / w
        self.last_bbox = bbox
        self.fall_candidate_time: Optional[float] = None
        self.last_centroid: Optional[Tuple[float, float]] = None

class UnusualActivityClassifier(BehavioralClassifierBase):
    """
    Rule-based Unusual Activity Classifier:
    Detects security and operational anomalies using geometric and kinematic heuristics:
    1. Running / Panic Fast Motion: Target ground/pixel velocity exceeding running threshold.
    2. Crowd Gathering: Cluster of N or more persons in close spatial proximity.
    3. Sudden Fall / Collapse: Rapid transition from standing aspect ratio (H/W > 1.3) to flat (H/W < 0.75).
    4. Counter-Flow / Wrong-Way Movement: Motion vector opposing defined directional flow.
    """
    def __init__(
        self,
        running_threshold_mps: float = 2.5,
        crowd_min_count: int = 4,
        crowd_radius_m: float = 2.0,
        flow_direction_deg: Optional[float] = None,
        enabled_rules: Optional[Dict[str, bool]] = None
    ):
        self.running_threshold = running_threshold_mps
        self.crowd_min_count = crowd_min_count
        self.crowd_radius = crowd_radius_m
        self.flow_direction_deg = flow_direction_deg
        
        self.enabled_rules = enabled_rules or {
            "running": True,
            "crowd": True,
            "fall": True,
            "counterflow": True
        }

        self.track_states: Dict[int, UnusualActivityState] = {}
        self.last_update: Dict[int, float] = {}
        self.last_crowd_alert_ts: float = -999.0

    def update(
        self,
        track_id: int,
        centroid: Tuple[float, float],
        frame_timestamp: float,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Expects kwargs:
            ema_velocity: float (ground plane or pixel velocity per second)
            bbox: Optional[Tuple[float, float, float, float]] (x1, y1, x2, y2)
            all_centroids: Optional[Dict[int, Tuple[float, float]]] (all active person centroids in frame)
        """
        self.last_update[track_id] = frame_timestamp
        ema_velocity = kwargs.get("ema_velocity", 0.0)
        bbox = kwargs.get("bbox")
        all_centroids = kwargs.get("all_centroids", {})

        if track_id not in self.track_states:
            self.track_states[track_id] = UnusualActivityState(track_id, frame_timestamp, bbox)
            self.track_states[track_id].last_centroid = centroid
            return None

        state = self.track_states[track_id]

        # 1. Evaluate Running / Rapid Panic Motion
        if self.enabled_rules.get("running", True):
            if ema_velocity >= self.running_threshold:
                state.consecutive_fast_count += 1
            else:
                state.consecutive_fast_count = max(0, state.consecutive_fast_count - 1)

            if state.consecutive_fast_count >= 3:
                logger.warn("Unusual Running / Fast Motion Detected!", track_id=track_id, velocity=ema_velocity)
                state.consecutive_fast_count = 0  # reset after firing
                return {
                    "event": "UNUSUAL_RUNNING",
                    "track_id": track_id,
                    "timestamp": frame_timestamp,
                    "anomaly_type": "running",
                    "description": f"Target P{track_id} detected running at high speed ({ema_velocity:.2f} m/s)."
                }

        # 2. Evaluate Sudden Fall / Collapse Anomaly
        if self.enabled_rules.get("fall", True) and bbox is not None:
            x1, y1, x2, y2 = bbox
            w = max(1.0, x2 - x1)
            h = max(1.0, y2 - y1)
            curr_aspect_ratio = h / w

            # Drop from standing (H/W > 1.2) to lying flat (H/W < 0.75)
            if state.initial_aspect_ratio > 1.2 and curr_aspect_ratio < 0.75:
                if state.fall_candidate_time is None:
                    state.fall_candidate_time = frame_timestamp
                elif frame_timestamp - state.fall_candidate_time >= 1.0 and ema_velocity < 0.5:
                    logger.warn("Unusual Sudden Fall / Collapse Detected!", track_id=track_id)
                    state.fall_candidate_time = None
                    return {
                        "event": "UNUSUAL_FALL_DETECTED",
                        "track_id": track_id,
                        "timestamp": frame_timestamp,
                        "anomaly_type": "fall",
                        "description": f"Target P{track_id} sudden posture collapse / fall detected."
                    }
            else:
                if curr_aspect_ratio > 1.0:
                    state.fall_candidate_time = None

        # 3. Evaluate Wrong-Way Counter-Flow
        if self.enabled_rules.get("counterflow", True) and self.flow_direction_deg is not None and state.last_centroid:
            dx = centroid[0] - state.last_centroid[0]
            dy = centroid[1] - state.last_centroid[1]
            dist = math.sqrt(dx**2 + dy**2)
            if dist > 15.0:  # significant movement step
                # Angle in degrees (0 = right, 90 = down)
                move_angle = math.degrees(math.atan2(dy, dx)) % 360
                target_angle = self.flow_direction_deg % 360
                diff = abs(move_angle - target_angle)
                if diff > 180:
                    diff = 360 - diff
                
                if diff > 120.0:  # Moving in opposite direction
                    logger.warn("Unusual Counter-Flow Movement Detected!", track_id=track_id, diff=diff)
                    return {
                        "event": "UNUSUAL_COUNTERFLOW",
                        "track_id": track_id,
                        "timestamp": frame_timestamp,
                        "anomaly_type": "counterflow",
                        "description": f"Target P{track_id} moving in counter-flow direction (deviation: {int(diff)}°)."
                    }

        # 4. Evaluate Crowd Gathering Density Anomaly (Multi-person spatial check)
        if self.enabled_rules.get("crowd", True) and len(all_centroids) >= self.crowd_min_count:
            if frame_timestamp - self.last_crowd_alert_ts > 10.0:  # 10s cooldown for crowd
                close_neighbors = 0
                for other_id, other_pos in all_centroids.items():
                    if other_id != track_id:
                        dist_px = math.sqrt((centroid[0] - other_pos[0])**2 + (centroid[1] - other_pos[1])**2)
                        if dist_px < 150.0:
                            close_neighbors += 1
                
                if close_neighbors >= (self.crowd_min_count - 1):
                    self.last_crowd_alert_ts = frame_timestamp
                    logger.warn("Unusual Crowd Gathering Anomaly Detected!", camera_crowd_count=close_neighbors+1)
                    return {
                        "event": "UNUSUAL_CROWD_GATHERING",
                        "track_id": track_id,
                        "timestamp": frame_timestamp,
                        "anomaly_type": "crowd",
                        "description": f"Abnormal crowd density detected: {close_neighbors + 1} people clustered in close proximity."
                    }

        state.last_centroid = centroid
        state.last_bbox = bbox
        state.last_ts = frame_timestamp
        return None

    def reset(self) -> None:
        self.track_states.clear()
        self.last_update.clear()

    def cleanup(self, max_age_seconds: float = 60.0) -> None:
        curr_time = time.time()
        for track_id, last_ts in list(self.last_update.items()):
            if curr_time - last_ts > max_age_seconds:
                self.track_states.pop(track_id, None)
                self.last_update.pop(track_id, None)
