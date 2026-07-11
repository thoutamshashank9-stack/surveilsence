import time
from typing import Dict, Tuple, Optional
from shapely.geometry import LineString
from app.core.logging import get_logger

logger = get_logger(__name__)

class DoubleLineState:
    def __init__(self):
        self.crossed_A: bool = False
        self.t_A: float = 0.0
        self.crossed_B: bool = False
        self.t_B: float = 0.0

class DoubleLineTripwire:
    """
    Implements double-line crossing tripwire with spatial and temporal hysteresis.
    A crossing event is only registered if a track ID sequentially crosses 
    Line A and then Line B within a maximum time threshold window.
    """
    def __init__(self, line_a: LineString, line_b: LineString, max_crossing_time_seconds: float = 3.0):
        self.line_a = line_a
        self.line_b = line_b
        self.max_crossing_time = max_crossing_time_seconds
        self.track_states: Dict[int, DoubleLineState] = {}
        self.last_update: Dict[int, float] = {}

    def update(
        self,
        track_id: int,
        prev_pos: Tuple[float, float],
        curr_pos: Tuple[float, float],
        timestamp: float
    ) -> Optional[str]:
        """
        Processes movement from prev_pos to curr_pos.
        Returns direction ("in" | "out") if a valid double-line crossing occurred, else None.
        """
        self.last_update[track_id] = timestamp
        movement_line = LineString([prev_pos, curr_pos])

        if track_id not in self.track_states:
            self.track_states[track_id] = DoubleLineState()

        state = self.track_states[track_id]

        # 1. Check intersection with Line A
        if self.line_a.intersects(movement_line):
            state.crossed_A = True
            state.t_A = timestamp
            logger.debug("Track crossed Line A", track_id=track_id, timestamp=timestamp)

        # 2. Check intersection with Line B
        if self.line_b.intersects(movement_line):
            state.crossed_B = True
            state.t_B = timestamp
            logger.debug("Track crossed Line B", track_id=track_id, timestamp=timestamp)

        # 3. Evaluate crossing condition
        # If both are crossed, verify the order and timing
        if state.crossed_A and state.crossed_B:
            # Case 1: Cross A -> Cross B within time limit
            if state.t_B > state.t_A and (state.t_B - state.t_A) <= self.max_crossing_time:
                logger.info("Double line crossing verified: IN", track_id=track_id, dt=state.t_B - state.t_A)
                self.reset(track_id)
                return "in"
            
            # Case 2: Cross B -> Cross A within time limit
            if state.t_A > state.t_B and (state.t_A - state.t_B) <= self.max_crossing_time:
                logger.info("Double line crossing verified: OUT", track_id=track_id, dt=state.t_A - state.t_B)
                self.reset(track_id)
                return "out"

            # Reset if constraints violated (e.g. timeout)
            self.reset(track_id)

        # 4. Handle state timeout (if track has crossed A but does not reach B)
        if state.crossed_A and not state.crossed_B:
            if (timestamp - state.t_A) > self.max_crossing_time:
                logger.debug("Double line crossing timeout for Line A", track_id=track_id)
                self.reset(track_id)

        if state.crossed_B and not state.crossed_A:
            if (timestamp - state.t_B) > self.max_crossing_time:
                logger.debug("Double line crossing timeout for Line B", track_id=track_id)
                self.reset(track_id)

        return None

    def reset(self, track_id: int):
        if track_id in self.track_states:
            self.track_states.pop(track_id)

    def cleanup(self, max_age_seconds: float = 60.0):
        """
        Garbage collect states for inactive track IDs to prevent memory leaks.
        """
        curr_time = time.time()
        for track_id, last_ts in list(self.last_update.items()):
            if curr_time - last_ts > max_age_seconds:
                self.reset(track_id)
                self.last_update.pop(track_id)
