import cv2
import threading
import time
import logging
import numpy as np
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class CameraStream:
    """
    Threaded camera stream that continuously reads frames to prevent 
    OpenCV's internal buffer from causing latency/lag.
    """
    def __init__(self, source: str, camera_id: str, reconnect_delay: int = 5):
        self.source = source
        self.camera_id = camera_id
        self.reconnect_delay = reconnect_delay
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.ret = False
        self.frame: Optional[np.ndarray] = None
        self.lock = threading.Lock()
        self.running = True
        
        # Determine stream type for specific OpenCV backend optimizations
        self.is_network = isinstance(source, str) and (source.startswith("rtsp://") or source.startswith("http"))
        
        self._connect()
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()

    def _connect(self):
        """Initialize or reconnect the VideoCapture."""
        if self.cap is not None:
            self.cap.release()
            
        logger.info(f"[{self.camera_id}] Connecting to {self.source}...")
        
        if self.is_network:
            # Use FFMPEG backend for network streams, set TCP for RTSP to reduce packet loss artifacts
            if self.source.startswith("rtsp://"):
                self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
                self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
                self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)
            else:
                # HTTP MJPEG (IP Webcam)
                self.cap = cv2.VideoCapture(self.source)
        else:
            # Local file or USB webcam (0, 1, etc.)
            self.cap = cv2.VideoCapture(self.source)

        # CRITICAL: Keep buffer size to 1 to always get the latest frame
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not self.cap.isOpened():
            logger.error(f"[{self.camera_id}] Failed to open stream.")
        else:
            logger.info(f"[{self.camera_id}] Successfully connected.")

    def _update_loop(self):
        """Continuously grab frames in the background."""
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                time.sleep(self.reconnect_delay)
                self._connect()
                continue

            ret, frame = self.cap.read()
            if not ret:
                logger.warning(f"[{self.camera_id}] Stream disconnected or ended. Reconnecting...")
                self.cap.release()
                time.sleep(self.reconnect_delay)
                self._connect()
                continue

            with self.lock:
                self.ret = ret
                self.frame = frame

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Return the most recent frame."""
        with self.lock:
            return self.ret, self.frame.copy() if self.frame is not None else None

    def stop(self):
        self.running = False
        self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()


class CameraManager:
    """Manages multiple CameraStream instances."""
    def __init__(self, config: dict):
        self.streams: Dict[str, CameraStream] = {}
        cameras_cfg = config.get("cameras", [])
        
        for cam in cameras_cfg:
            cam_id = cam["id"]
            source = cam["source"]
            self.streams[cam_id] = CameraStream(source, cam_id)
            
    def get_frame(self, camera_id: str) -> Tuple[bool, Optional[np.ndarray]]:
        if camera_id not in self.streams:
            return False, None
        return self.streams[camera_id].read()

    def stop_all(self):
        logger.info("Stopping all camera streams...")
        for stream in self.streams.values():
            stream.stop()
