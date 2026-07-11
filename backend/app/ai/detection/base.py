import time
from dataclasses import dataclass
import numpy as np
from abc import ABC, abstractmethod
import supervision as sv

@dataclass
class ModelCapabilities:
    supports_nms_free: bool = False
    input_resolution: int = 640
    max_batch_size: int = 1

class DetectorBase(ABC):
    @abstractmethod
    def detect(self, frame: np.ndarray) -> sv.Detections:
        pass

    @abstractmethod
    def get_model_info(self) -> dict:
        pass

    @abstractmethod
    def get_capabilities(self) -> ModelCapabilities:
        pass

class MockDetector(DetectorBase):
    def __init__(self, confidence_threshold: float = 0.35):
        self.confidence_threshold = confidence_threshold
        self.start_time = time.time()

    def detect(self, frame: np.ndarray) -> sv.Detections:
        """Simulate multiple classes (person, vehicle, fire) moving inside the screen frame."""
        h, w, _ = frame.shape
        t = time.time() - self.start_time
        
        # Person 1 (moving across screen left to right)
        cx1 = int(w * 0.1 + (w * 0.8) * (0.5 + 0.5 * np.sin(t * 0.1)))
        cy1 = int(h * 0.4 + (h * 0.2) * (0.5 + 0.5 * np.cos(t * 0.15)))
        bw1, bh1 = 60, 140
        
        # Vehicle 1 (moving across bottom of checkout/lobby area)
        cx2 = int(w * 0.7 + (w * 0.1) * np.sin(t * 0.2))
        cy2 = int(h * 0.3 + (h * 0.4) * (0.5 + 0.5 * np.sin(t * 0.08)))
        bw2, bh2 = 90, 80
        
        # Simulate fire detection in top-left restricted area periodically
        fire_active = (int(t) % 30) > 15
        
        boxes = [
            [cx1 - bw1 // 2, cy1 - bh1 // 2, cx1 + bw1 // 2, cy1 + bh1 // 2],
            [cx2 - bw2 // 2, cy2 - bh2 // 2, cx2 + bw2 // 2, cy2 + bh2 // 2]
        ]
        scores = [0.92, 0.87]
        labels = [0, 2] # 0 = person, 2 = vehicle
        
        if fire_active:
            boxes.append([40, 40, 120, 120])
            scores.append(0.96)
            labels.append(80) # 80 = fire
            
        xyxy = np.array(boxes, dtype=np.float32)
        confidence = np.array(scores, dtype=np.float32)
        class_id = np.array(labels, dtype=np.int32)
        
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

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supports_nms_free=True,
            input_resolution=640,
            max_batch_size=4
        )
