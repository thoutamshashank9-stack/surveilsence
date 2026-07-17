from typing import Dict, Tuple, List, Optional, Any
import supervision as sv
from app.config import Settings
from app.ai.tracking.bytetrack import ByteTrackTracker

class TrackingManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.trackers: Dict[str, ByteTrackTracker] = {}
        # Stores history of point coordinates: camera_id -> Dict[track_id, List[Tuple[float, float, float]]] (x, y, timestamp)
        self.track_history: Dict[str, Dict[int, List[Tuple[float, float, float]]]] = {}
        
        self.reid_matcher = None
        reid_cfg = self.settings.inference.tracking.cross_camera.reid
        if self.settings.inference.tracking.cross_camera.enabled and reid_cfg.enabled:
            model_path = reid_cfg.model_path
            # Fallback to check if empty/non-existent
            from pathlib import Path
            if not model_path or not Path(model_path).exists():
                try:
                    from app.services.model_registry import ModelRegistry
                    registry = ModelRegistry(settings)
                    model_path = registry.get_model_path("osnet_x0_25", "tracking")
                except Exception:
                    model_path = None
            
            if model_path and Path(model_path).exists():
                try:
                    from app.ai.tracking.reid import ReIDMatcher
                    from app.ai.backends.factory import select_backend
                    backend = select_backend(self.settings.inference.backend)
                    self.reid_matcher = ReIDMatcher(
                        onnx_path=model_path,
                        dim=reid_cfg.embedding_dim,
                        threshold=reid_cfg.match_threshold,
                        backend=backend
                    )
                except Exception as e:
                    # Let it gracefully continue without Re-ID if it fails to compile/load
                    pass

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

    def assign_global_ids(self, camera_id: str, detections: sv.Detections, frame: Optional[Any] = None) -> Dict[int, int]:
        """
        Runs Re-ID matching on person crops and returns a dict mapping local track_id -> global_person_id.
        """
        mapping = {}
        if self.reid_matcher is None or frame is None or detections.tracker_id is None:
            return mapping

        import time
        import numpy as np
        curr_time = time.time()
        h, w = frame.shape[:2]

        for idx, box in enumerate(detections.xyxy):
            class_id = int(detections.class_id[idx]) if detections.class_id is not None else 0
            if class_id != 0:
                continue

            track_id = int(detections.tracker_id[idx])
            x1, y1, x2, y2 = map(int, box)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            if x2 > x1 and y2 > y1:
                crop = frame[y1:y2, x1:x2]
                if crop.size > 0:
                    try:
                        global_id = self.reid_matcher.assign_global_id(
                            camera_id=camera_id,
                            track_id=track_id,
                            crop_bgr=crop,
                            ts=curr_time
                        )
                        mapping[track_id] = global_id
                    except Exception as e:
                        pass
        return mapping
