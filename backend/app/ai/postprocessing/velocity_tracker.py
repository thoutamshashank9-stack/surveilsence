import time
import math
from typing import Dict, Tuple, Optional
from app.ai.postprocessing.homography import HomographyCalibrator
from app.core.logging import get_logger

logger = get_logger(__name__)

class VelocityState:
    def __init__(self, x: float, y: float, timestamp: float):
        self.last_x = x
        self.last_y = y
        self.last_ts = timestamp
        self.ema_velocity: float = 0.0

class VelocityTracker:
    """
    Tracks velocity of moving targets on the ground-plane Cartesian coordinate 
    system in meters, corrected by perspective homography.
    Uses Exponential Moving Average (EMA) to smooth out detection jitter.
    """
    def __init__(self, alpha: float = 0.15, homography: Optional[HomographyCalibrator] = None):
        self.alpha = alpha
        self.homography = homography
        self.track_states: Dict[int, VelocityState] = {}
        self.last_update: Dict[int, float] = {}

    def update(self, track_id: int, pixel_x: float, pixel_y: float, timestamp: float) -> float:
        """
        Calculates and updates ground-plane velocity for a track ID.
        Returns the updated EMA velocity in meters per second (or pixels/second if not calibrated).
        """
        self.last_update[track_id] = timestamp
        
        # 1. Project to ground-plane Cartesian coordinate if calibrated
        if self.homography and self.homography.is_calibrated():
            world_x, world_y = self.homography.pixel_to_world(pixel_x, pixel_y)
        else:
            # Fallback to pixels
            world_x, world_y = pixel_x, pixel_y

        if track_id not in self.track_states:
            self.track_states[track_id] = VelocityState(world_x, world_y, timestamp)
            return 0.0

        state = self.track_states[track_id]
        dt = timestamp - state.last_ts

        if dt <= 0:
            return state.ema_velocity

        # 2. Calculate instantaneous velocity
        dx = world_x - state.last_x
        dy = world_y - state.last_y
        dist = math.sqrt(dx**2 + dy**2)
        inst_v = dist / dt

        # 3. Apply Exponential Moving Average (EMA) smoothing
        # V_ema_t = alpha * V_t + (1 - alpha) * V_ema_t-1
        state.ema_velocity = self.alpha * inst_v + (1.0 - self.alpha) * state.ema_velocity

        # Update state position and timestamp
        state.last_x = world_x
        state.last_y = world_y
        state.last_ts = timestamp

        return state.ema_velocity

    def get_ema_velocity(self, track_id: int) -> float:
        if track_id in self.track_states:
            return self.track_states[track_id].ema_velocity
        return 0.0

    def cleanup(self, max_age_seconds: float = 60.0):
        curr_time = time.time()
        for track_id, last_ts in list(self.last_update.items()):
            if curr_time - last_ts > max_age_seconds:
                self.track_states.pop(track_id, None)
                self.last_update.pop(track_id, None)
