import time
import logging
import numpy as np
from typing import Dict, Set
from logger import EventLogger
from db_manager import DBManager

logger = logging.getLogger(__name__)

class TrackState:
    def __init__(self, track_id: int, camera_id: str, start_ts: float):
        self.track_id = track_id
        self.camera_id = camera_id
        self.start_ts = start_ts
        self.last_seen_ts = start_ts
        
        self.current_zones: Dict[str, float] = {}  # zone_name -> entry_timestamp
        self.visited_zones: Set[str] = set()
        self.has_checkout = False
        self.role = "unknown"  # 'customer', 'worker'

class EventEngine:
    def __init__(self, config: dict, event_logger: EventLogger, db_manager: DBManager):
        self.config = config
        self.rules = config.get("rules", {})
        self.logger = event_logger
        self.db = db_manager
        
        # track_id -> TrackState
        self.active_tracks: Dict[int, TrackState] = {}
        self.worker_cabin_min_seconds = self.rules.get("worker_cabin_min_seconds", 60)

    def update(self, camera_id: str, detections, polygon_states: dict, line_crossings: dict, frame_ts: float):
        current_frame_track_ids = set()
        
        if detections.tracker_id is not None:
            for i, track_id in enumerate(detections.tracker_id):
                if track_id is None: continue
                current_frame_track_ids.add(track_id)
                
                # 1. Initialize or update track state
                if track_id not in self.active_tracks:
                    self.active_tracks[track_id] = TrackState(track_id, camera_id, frame_ts)
                    self._emit_event(frame_ts, camera_id, track_id, "track_started")
                
                state = self.active_tracks[track_id]
                state.last_seen_ts = frame_ts

                # 2. Process Line Crossings (Entry/Exit)
                for zone_name, (crossed_in, crossed_out) in line_crossings.items():
                    if crossed_in[i]:
                        self._emit_event(frame_ts, camera_id, track_id, "person_entered_store", zone_name)
                    if crossed_out[i]:
                        self._handle_exit(frame_ts, camera_id, track_id, state, zone_name)

                # 3. Process Polygon Zones (Dwell)
                for zone_name, mask in polygon_states.items():
                    if mask[i]:
                        # Person is inside this zone
                        if zone_name not in state.current_zones:
                            # Just entered
                            state.current_zones[zone_name] = frame_ts
                            state.visited_zones.add(zone_name)
                            self._emit_event(frame_ts, camera_id, track_id, "dwell_start", zone_name)
                            
                            # Check for checkout visit
                            if zone_name == "checkout":
                                state.has_checkout = True
                    else:
                        # Person is NOT inside this zone
                        if zone_name in state.current_zones:
                            # Just left
                            entry_ts = state.current_zones.pop(zone_name)
                            duration = frame_ts - entry_ts
                            self._emit_event(frame_ts, camera_id, track_id, "dwell_end", zone_name, duration)
                            
                            # Worker Logic: If they spent > X seconds in cabin, mark as worker
                            if zone_name == "worker_cabin" and duration > self.worker_cabin_min_seconds:
                                if state.role != "worker":
                                    logger.info(f"Track {track_id} identified as WORKER based on cabin dwell ({duration:.1f}s)")
                                    state.role = "worker"

        # 4. Handle Track Termination (Lost tracks or exited)
        lost_tracks = set(self.active_tracks.keys()) - current_frame_track_ids
        for track_id in lost_tracks:
            state = self.active_tracks[track_id]
            
            # Force close any open zones
            for zone_name, entry_ts in list(state.current_zones.items()):
                duration = frame_ts - entry_ts
                self._emit_event(frame_ts, camera_id, track_id, "dwell_end", zone_name, duration)
                state.current_zones.pop(zone_name)

            # Finalize Track Summary
            total_duration = state.last_seen_ts - state.start_ts
            self.db.upsert_track_summary(
                track_id=track_id,
                camera_id=camera_id,
                start_ts=state.start_ts,
                end_ts=state.last_seen_ts,
                role=state.role,
                has_checkout=state.has_checkout,
                total_duration_s=total_duration
            )
            
            # No-Purchase Exit Logic
            if state.role == "customer" and not state.has_checkout and len(state.visited_zones) > 1:
                 self._emit_event(frame_ts, camera_id, track_id, "no_purchase_exit", metadata={
                     "visited_zones": list(state.visited_zones),
                     "total_time_s": total_duration
                 })

            self._emit_event(frame_ts, camera_id, track_id, "track_ended", metadata={"role": state.role})
            del self.active_tracks[track_id]

    def _handle_exit(self, frame_ts: float, camera_id: str, track_id: int, state: TrackState, zone_name: str):
        """Handle person exiting through a line zone."""
        self._emit_event(frame_ts, camera_id, track_id, "person_exited_store", zone_name)
        
        # Clean up will happen in the main loop when track is lost

    def _emit_event(self, ts, camera_id, track_id, event_type, zone_name=None, duration_s=None, metadata=None):
        # Convert numpy types to Python native types for JSON serialization
        if isinstance(track_id, np.integer):
            track_id = int(track_id)
        
        event = {
            "ts": float(ts),
            "camera_id": str(camera_id),
            "track_id": int(track_id),
            "event_type": str(event_type),
            "zone_name": str(zone_name) if zone_name else None,
            "duration_s": float(duration_s) if duration_s is not None else None,
            "metadata": metadata or {}
        }
        self.logger.log_event(event)
        self.db.insert_event(
            ts=ts, camera_id=camera_id, track_id=int(track_id), 
            event_type=event_type, zone_name=zone_name, 
            duration_s=duration_s, metadata=metadata
        )
