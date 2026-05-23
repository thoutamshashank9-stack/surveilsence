import cv2
import numpy as np
import supervision as sv
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

class BaseDetector:
    def detect(self, frame: np.ndarray) -> sv.Detections:
        raise NotImplementedError

class MockDetector(BaseDetector):
    """Generates fake detections for pipeline testing without a GPU/Model."""
    def __init__(self, num_mock_people=2):
        self.num_mock_people = num_mock_people
        self.frame_count = 0

    def detect(self, frame: np.ndarray) -> sv.Detections:
        h, w, _ = frame.shape
        self.frame_count += 1
        
        # Simulate movement
        x_offset = (self.frame_count * 2) % w
        
        xyxy = []
        confidence = []
        class_id = []
        
        for i in range(self.num_mock_people):
            x1 = (x_offset + i * 150) % w
            y1 = int(h * 0.3)
            x2 = x1 + 80
            y2 = y1 + 180
            xyxy.append([x1, y1, x2, y2])
            confidence.append(0.95)
            class_id.append(0) # 0 is 'person' in COCO

        return sv.Detections(
            xyxy=np.array(xyxy),
            confidence=np.array(confidence),
            class_id=np.array(class_id)
        )

class RFDetrDetector(BaseDetector):
    """Real-time detection using Roboflow's RF-DETR."""
    def __init__(self, model_size: str = "rfdetr-medium", confidence: float = 0.45, device: str = "cuda"):
        logger.info(f"Loading RF-DETR model: {model_size} on {device}...")
        try:
            from rfdetr import RFDETRMedium, RFDETRSmall, RFDETRNano
            
            # Map string config to actual classes
            model_map = {
                "rfdetr-nano": RFDETRNano,
                "rfdetr-small": RFDETRSmall,
                "rfdetr-medium": RFDETRMedium
            }
            
            model_class = model_map.get(model_size, RFDETRMedium)
            self.model = model_class()
            self.confidence = confidence
            logger.info("RF-DETR model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load RF-DETR: {e}. Falling back to MockDetector.")
            self.model = None

    def detect(self, frame: np.ndarray) -> sv.Detections:
        if self.model is None:
            return sv.Detections.empty()
            
        # RF-DETR expects an image path or numpy array. 
        # We use supervision to standardize the output.
        detections = self.model.predict(frame, threshold=self.confidence)
        
        # Filter only for 'person' class (COCO class ID 0)
        person_mask = detections.class_id == 0
        return detections[person_mask]

def get_detector(config: dict) -> BaseDetector:
    """Factory function to return the correct detector based on config."""
    model_cfg = config.get("model", {})
    model_type = model_cfg.get("type", "mock").lower()
    
    if model_type == "rfdetr":
        return RFDetrDetector(
            model_size=model_cfg.get("size", "rfdetr-medium"),
            confidence=model_cfg.get("confidence", 0.45),
            device=model_cfg.get("device", "cuda")
        )
    else:
        logger.info("Using MockDetector for testing.")
        return MockDetector()
