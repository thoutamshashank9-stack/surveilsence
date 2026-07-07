from typing import Dict, Tuple, List, Optional
import supervision as sv
from app.config import Settings
from app.ai.tracking.bytetrack import ByteTrackTracker

class TrackingManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.trackers: Dict[str, ByteTrackTracker] = {}
        # Stores history of point coordinates: camera_id -> Dict[track_id, List[Tuple[float, float, float]]] (x, y, timestamp)
        self.track_history: Dict[str, Dict[int, List[Tuple[float, float, float]]]] = {}

    def _get_tracker(self, camera_id: str) -> ByteTrackTracker:
        if camera_id not in self.trackers:
            cfg = self.settings.inference.tracking
            self.trackers[camera_id] = ByteTrackTracker(
                track_activation_threshold=cfg.track_activation_threshold,
                lost_track_buffer=cfg.lost_track_buffer,
                minimum_matching_threshold=cfg.minimum_matching_threshold,
                frame_rate=cfg.frame_rate,
                minimum_consecutive_frames=cfg.minimum_consecutive_frames
            )
            self.track_history[camera_id] = {}
        return self.trackers[camera_id]

    def update(self, camera_id: str, detections: sv.Detections) -> sv.Detections:
        tracker = self._get_tracker(camera_id)
        tracked_detections = tracker.update(detections)
        
        # Log histories
        if tracked_detections.tracker_id is not None:
            import time
            curr_time = time.time()
            
            for idx, box in enumerate(tracked_detections.xyxy):
                track_id = int(tracked_detections.tracker_id[idx])
                
                # Bottom center anchor (feet position)
                bx = (box[0] + box[2]) / 2
                by = box[3]
                
                if track_id not in self.track_history[camera_id]:
                    self.track_history[camera_id][track_id] = []
                    
                self.track_history[camera_id][track_id].append((bx, by, curr_time))
                
                # Keep last 1000 points per track
                if len(self.track_history[camera_id][track_id]) > 1000:
                    self.track_history[camera_id][track_id].pop(0)
                    
        return tracked_detections

    def get_history(self, camera_id: str, track_id: int) -> List[Tuple[float, float, float]]:
        if camera_id in self.track_history and track_id in self.track_history[camera_id]:
            return self.track_history[camera_id][track_id]
        return []

    def clear_track(self, camera_id: str, track_id: int) -> None:
        if camera_id in self.track_history and track_id in self.track_history[camera_id]:
            self.track_history[camera_id].pop(track_id)

    def reset(self, camera_id: str) -> None:
        if camera_id in self.trackers:
            self.trackers[camera_id].reset()
        if camera_id in self.track_history:
            self.track_history[camera_id].clear()
