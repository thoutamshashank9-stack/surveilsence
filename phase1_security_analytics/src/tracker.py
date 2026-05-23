import supervision as sv
import logging

logger = logging.getLogger(__name__)

class ObjectTracker:
    """Wraps Supervision's ByteTrack for multi-object tracking."""
    def __init__(self, config: dict):
        track_cfg = config.get("tracking", {})
        
        # ByteTrack configuration - using new API parameters
        self.tracker = sv.ByteTrack(
            track_activation_threshold=track_cfg.get("track_thresh", 0.4),
            minimum_consecutive_frames=track_cfg.get("track_buffer", 30),
            minimum_matching_threshold=track_cfg.get("match_thresh", 0.8)
        )
        logger.info("ByteTrack initialized.")

    def update(self, detections: sv.Detections) -> sv.Detections:
        """
        Updates tracker with new detections.
        Returns detections with `tracker_id` assigned.
        """
        # ByteTrack natively integrates with supervision Detections
        return self.tracker.update_with_detections(detections)

    def reset(self):
        """Reset tracker state (e.g., at the end of the day)."""
        self.tracker.reset()
