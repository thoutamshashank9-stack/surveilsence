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

    def _connect(self) -> bool:
        self._disconnect()
        if self.cam_type == "mock":
            self.status = CameraStatus.ONLINE
            logger.info("Camera connected (mock mode)", camera_id=self.camera_id)
            return True
            
        try:
            logger.info("Connecting to camera stream...", camera_id=self.camera_id, source=self.source)
            if self.source.isdigit():
                # USB Camera
                self.cap = cv2.VideoCapture(int(self.source))
            else:
                self.cap = cv2.VideoCapture(self.source)
                
            if self.cap.isOpened():
                self.status = CameraStatus.ONLINE
                logger.info("Camera connected successfully", camera_id=self.camera_id)
                return True
            else:
                self.status = CameraStatus.ERROR
                logger.error("Failed to open camera source", camera_id=self.camera_id)
                return False
        except Exception as e:
            self.status = CameraStatus.ERROR
            logger.error("Error during camera connection", camera_id=self.camera_id, error=str(e))
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
                self.frame = self._generate_mock_frame()
                self.last_frame_time = time.time()
            else:
                if self.cap:
                    ret, img = self.cap.read()
                    if ret:
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
        
    async def add_camera(self, config: Any) -> None:
        camera_id = config.id if hasattr(config, "id") else config.get("id")
        name = config.name if hasattr(config, "name") else config.get("name")
        source = config.source if hasattr(config, "source") else config.get("source")
        type_ = config.type if hasattr(config, "type") else config.get("type")
        fps_cap = config.fps_cap if hasattr(config, "fps_cap") else config.get("fps_cap", 30)
        
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
