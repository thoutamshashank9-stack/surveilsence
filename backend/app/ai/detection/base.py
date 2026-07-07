import time
import numpy as np
from abc import ABC, abstractmethod
import supervision as sv

class DetectorBase(ABC):
    @abstractmethod
    def detect(self, frame: np.ndarray) -> sv.Detections:
        pass

    @abstractmethod
    def get_model_info(self) -> dict:
        pass

class MockDetector(DetectorBase):
    def __init__(self, confidence_threshold: float = 0.35):
        self.confidence_threshold = confidence_threshold
        self.start_time = time.time()

    def detect(self, frame: np.ndarray) -> sv.Detections:
        """Simulate two people moving inside the screen frame."""
        h, w, _ = frame.shape
        t = time.time() - self.start_time
        
        # Person 1 (moving across screen left to right)
        cx1 = int(w * 0.1 + (w * 0.8) * (0.5 + 0.5 * np.sin(t * 0.1)))
        cy1 = int(h * 0.4 + (h * 0.2) * (0.5 + 0.5 * np.cos(t * 0.15)))
        bw1, bh1 = 60, 140
        
        # Person 2 (moving up and down checkout area)
        cx2 = int(w * 0.7 + (w * 0.1) * np.sin(t * 0.2))
        cy2 = int(h * 0.3 + (h * 0.4) * (0.5 + 0.5 * np.sin(t * 0.08)))
        bw2, bh2 = 55, 130
        
        xyxy = np.array([
            [cx1 - bw1 // 2, cy1 - bh1 // 2, cx1 + bw1 // 2, cy1 + bh1 // 2],
            [cx2 - bw2 // 2, cy2 - bh2 // 2, cx2 + bw2 // 2, cy2 + bh2 // 2]
        ], dtype=np.float32)
        
        confidence = np.array([0.92, 0.87], dtype=np.float32)
        class_id = np.array([0, 0], dtype=np.int32)
        
        # Keep inside bounds
        xyxy[:, [0, 2]] = np.clip(xyxy[:, [0, 2]], 0, w)
        xyxy[:, [1, 3]] = np.clip(xyxy[:, [1, 3]], 0, h)
        
        return sv.Detections(
            xyxy=xyxy,
            confidence=confidence,
            class_id=class_id
        )

    def get_model_info(self) -> dict:
        return {
            "model": "mock",
            "type": "mock_generator",
            "classes": ["person"],
            "license": "Public Domain"
        }
