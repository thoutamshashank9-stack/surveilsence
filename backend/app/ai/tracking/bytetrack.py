import supervision as sv
from app.ai.tracking.base import TrackerBase

class ByteTrackTracker(TrackerBase):
    def __init__(
        self,
        track_activation_threshold: float = 0.25,
        lost_track_buffer: int = 30,
        minimum_matching_threshold: float = 0.8,
        frame_rate: int = 30,
        minimum_consecutive_frames: int = 1
    ):
        self.track_activation_threshold = track_activation_threshold
        self.lost_track_buffer = lost_track_buffer
        self.minimum_matching_threshold = minimum_matching_threshold
        self.frame_rate = frame_rate
        self.minimum_consecutive_frames = minimum_consecutive_frames
        
        self._init_tracker()

    def _init_tracker(self) -> None:
        self.tracker = sv.ByteTrack(
            track_activation_threshold=self.track_activation_threshold,
            lost_track_buffer=self.lost_track_buffer,
            minimum_matching_threshold=self.minimum_matching_threshold,
            frame_rate=self.frame_rate,
            minimum_consecutive_frames=self.minimum_consecutive_frames
        )

    def update(self, detections: sv.Detections) -> sv.Detections:
        return self.tracker.update_with_detections(detections)

    def reset(self) -> None:
        # Reset tracking state by re-initializing the supervision ByteTrack instance
        self._init_tracker()
