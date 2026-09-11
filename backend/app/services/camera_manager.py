import cv2
import time
import threading
from typing import Dict, Optional, Tuple, Any
import numpy as np

from app.models.enums import CameraStatus, CameraType
from app.core.logging import get_logger
from app.core.events import EventBus
from app.models.enums import EventType

logger = get_logger(__name__)

class CameraStream:
    def __init__(self, camera_id: str, name: str, source: str, cam_type: str, fps_cap: int = 30):
        self.camera_id = camera_id
        self.name = name
        self.source = source
        self.cam_type = cam_type
        self.fps_cap = fps_cap
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame: Optional[np.ndarray] = None
        self.last_frame_time: float = 0.0
        self._lock = threading.Lock()
        
        self.status = CameraStatus.OFFLINE
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        self.reconnect_delay = 5.0
        self.frame_delay = 1.0 / fps_cap

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.status = CameraStatus.CONNECTING
        self.thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.thread.start()
        logger.info("Camera stream thread started", camera_id=self.camera_id)

    def stop(self) -> None:
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        self._disconnect()
        self.status = CameraStatus.OFFLINE
        logger.info("Camera stream thread stopped", camera_id=self.camera_id)

    def _resolve_candidate_sources(self) -> list:
        """Resolve common IP Webcam, DroidCam, and RTSP stream variations if base URL provided."""
        sources = [self.source]
        s = self.source.strip()
        
        import re
        ip_match = re.search(r'(?:https?|rtsp)://([^/]+)(?:/(.*))?', s, re.IGNORECASE)
        if ip_match:
            host_port = ip_match.group(1)
            path = (ip_match.group(2) or "").strip()
            
            # If path is empty, root, or missing specific video extension
            if not path or path == "/":
                candidates = [
                    f"rtsp://{host_port}/h264_pcm.sdp",
                    f"rtsp://{host_port}/h264_ulaw.sdp",
                    f"rtsp://{host_port}/h264_aac.sdp",
                    f"http://{host_port}/video",
                    f"http://{host_port}/videofeed",
                    f"rtsp://{host_port}/live",
                ]
                for c in candidates:
                    if c not in sources:
                        sources.append(c)
            elif s.lower().startswith("https://"):
                sources.append(f"http://{host_port}/{path}")
                sources.append(f"rtsp://{host_port}/{path}")
                if "8080" in host_port and not path.endswith(".sdp"):
                    sources.append(f"rtsp://{host_port}/h264_pcm.sdp")
                    sources.append(f"http://{host_port}/video")
            elif s.lower().startswith("http://") and "8080" in host_port and not path.endswith((".sdp", "video", "videofeed")):
                sources.append(f"rtsp://{host_port}/h264_pcm.sdp")
                sources.append(f"http://{host_port}/video")
        return sources

    def _connect(self) -> bool:
        self._disconnect()
        if self.cam_type == "mock":
            self.status = CameraStatus.ONLINE
            logger.info("Camera connected (mock mode)", camera_id=self.camera_id)
            return True
            
        candidate_sources = self._resolve_candidate_sources()
        for src in candidate_sources:
            try:
                logger.info("Connecting to camera stream...", camera_id=self.camera_id, source=src)
                if src.isdigit():
                    # USB Camera
                    self.cap = cv2.VideoCapture(int(src))
                else:
                    if src.lower().startswith("rtsp://"):
                        import os
                        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
                        self.cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
                    else:
                        self.cap = cv2.VideoCapture(src)
                    
                if self.cap and self.cap.isOpened():
                    ret, test_frame = self.cap.read()
                    if ret and test_frame is not None:
                        try:
                            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        except Exception:
                            pass
                        with self._lock:
                            self.frame = test_frame
                            self.last_frame_time = time.time()
                        self.source = src
                        self.status = CameraStatus.ONLINE
                        logger.info("Camera connected successfully", camera_id=self.camera_id, active_source=src)
                        return True
                    else:
                        self.cap.release()
                        self.cap = None
            except Exception as e:
                logger.debug("Candidate stream connection failed", camera_id=self.camera_id, source=src, error=str(e))
                if self.cap:
                    self.cap.release()
                    self.cap = None

        self.status = CameraStatus.ERROR
        logger.error("Failed to open camera source candidates", camera_id=self.camera_id, candidates=candidate_sources)
        return False

    def _disconnect(self) -> None:
        if self.cap:
            self.cap.release()
            self.cap = None

    def _stream_loop(self) -> None:
        while self.running:
            if self.status != CameraStatus.ONLINE:
                if not self._connect():
                    time.sleep(self.reconnect_delay)
                    continue

            # Ingestion
            start_time = time.time()
            
            if self.cam_type == "mock":
                # Generate mock frame
                mock_frame = self._generate_mock_frame()
                with self._lock:
                    self.frame = mock_frame
                    self.last_frame_time = time.time()
            else:
                if self.cap:
                    ret, img = self.cap.read()
                    if ret:
                        with self._lock:
                            self.frame = img
                            self.last_frame_time = time.time()
                    else:
                        logger.warn("Failed to read frame from camera, attempting reconnect", camera_id=self.camera_id)
                        self.status = CameraStatus.CONNECTING
                        time.sleep(1.0)
                        continue

            # Sleep to match frame cap
            elapsed = time.time() - start_time
            sleep_time = max(0.0, self.frame_delay - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self._lock:
            if self.status != CameraStatus.ONLINE or self.frame is None:
                return False, None
            return True, self.frame.copy()

    def _generate_mock_frame(self) -> np.ndarray:
        # Generate 640x480 dark grey canvas
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (30, 30, 30)
        
        # Grid lines
        for x in range(0, 640, 50):
            cv2.line(frame, (x, 0), (x, 480), (45, 45, 45), 1)
        for y in range(0, 480, 50):
            cv2.line(frame, (0, y), (640, y), (45, 45, 45), 1)
            
        # Draw camera name & timestamp
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"CAM: {self.name} ({self.camera_id})", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 180, 255), 2)
        cv2.putText(frame, ts, (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)
        
        # Add a simulated moving square in background
        t = time.time()
        cx = int(320 + 200 * np.sin(t * 0.8))
        cy = int(240 + 100 * np.cos(t * 0.5))
        cv2.rectangle(frame, (cx - 20, cy - 20), (cx + 20, cy + 20), (0, 255, 100), -1)
        
        return frame


class CameraManager:
    def __init__(self, settings: Any, event_bus: EventBus):
        self.settings = settings
        self.event_bus = event_bus
        self.cameras: Dict[str, CameraStream] = {}
        
    @staticmethod
    def _validate_camera_source(source: str) -> None:
        """Validate camera source URL to prevent SSRF attacks."""
        import ipaddress
        from urllib.parse import urlparse

        if not source:
            raise ValueError("Camera source cannot be empty")

        # Allow digit-only sources (USB camera index)
        if source.isdigit():
            return

        # Allow 'mock' type
        if source == "mock":
            return

        # Allow local file paths (for testing with video files)
        if source.startswith("../") or source.startswith("./") or source.startswith("/"):
            return
        if len(source) > 1 and source[1] == ":":  # Windows drive paths like C:\...
            return

        ALLOWED_SCHEMES = {"rtsp", "rtsps", "http", "https", "rtmp"}
        try:
            parsed = urlparse(source)
        except Exception:
            raise ValueError(f"Invalid camera source URL: {source}")

        if parsed.scheme and parsed.scheme.lower() not in ALLOWED_SCHEMES:
            raise ValueError(f"Unsupported URL scheme '{parsed.scheme}'. Allowed: {ALLOWED_SCHEMES}")

        # Block private/loopback IP ranges (SSRF protection)
        if parsed.hostname:
            try:
                ip = ipaddress.ip_address(parsed.hostname)
                if ip.is_loopback or ip.is_link_local:
                    raise ValueError(f"Camera source cannot target loopback/link-local address: {parsed.hostname}")
            except ValueError as e:
                if "Camera source" in str(e):
                    raise
                # Not an IP address (hostname), allow it
                pass

    async def add_camera(self, config: Any) -> None:
        is_dict = isinstance(config, dict)
        
        camera_id = config.get("id") if is_dict else getattr(config, "id", None)
        name = config.get("name") if is_dict else getattr(config, "name", None)
        source = config.get("source") if is_dict else getattr(config, "source", None)
        self._validate_camera_source(source)
        
        # Extract type safely
        raw_type = config.get("type") if is_dict else getattr(config, "type", None)
        type_ = raw_type.value if hasattr(raw_type, "value") else str(raw_type)
        
        # Extract fps_cap safely (fall back to config_json if it is a DB model)
        if is_dict:
            fps_cap = config.get("fps_cap", 30)
        else:
            fps_cap = getattr(config, "fps_cap", None)
            if fps_cap is None:
                config_json = getattr(config, "config_json", {}) or {}
                fps_cap = config_json.get("fps_cap", 30)
        
        if camera_id in self.cameras:
            await self.remove_camera(camera_id)
            
        stream = CameraStream(camera_id, name, source, type_, fps_cap)
        stream.start()
        self.cameras[camera_id] = stream
        
        # Publish status change
        await self.event_bus.publish(
            EventType.DETECTION,  # Or camera status event
            {"camera_id": camera_id, "status": CameraStatus.ONLINE}
        )

    async def remove_camera(self, camera_id: str) -> None:
        if camera_id in self.cameras:
            stream = self.cameras.pop(camera_id)
            stream.stop()
            logger.info("Camera stream removed", camera_id=camera_id)

    def get_frame(self, camera_id: str) -> Tuple[bool, Optional[np.ndarray]]:
        if camera_id not in self.cameras:
            return False, None
        return self.cameras[camera_id].read()

    def get_status(self, camera_id: str) -> CameraStatus:
        if camera_id not in self.cameras:
            return CameraStatus.OFFLINE
        return self.cameras[camera_id].status

    async def stop_all(self) -> None:
        logger.info("Stopping all camera streams...")
        for stream in self.cameras.values():
            stream.stop()
        self.cameras.clear()
