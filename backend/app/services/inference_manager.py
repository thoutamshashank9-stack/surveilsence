from typing import Dict, Any, Optional
import numpy as np
import supervision as sv

from app.config import Settings
from app.ai.backends.factory import select_backend
from app.ai.detection.base import DetectorBase, MockDetector
from app.ai.detection.rtdetr import RTDetrDetector
from app.core.exceptions import InferenceError
from app.core.logging import get_logger

logger = get_logger(__name__)

class InferenceManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.backend = select_backend(settings.inference.backend)
        self.detector: Optional[DetectorBase] = None
        
        self._init_detector()

    def _init_detector(self) -> None:
        model_name = self.settings.inference.detection.model
        conf_thresh = self.settings.inference.detection.confidence_threshold
        classes = self.settings.inference.detection.classes
        input_size = tuple(self.settings.inference.detection.input_size)
        
        if model_name == "mock":
            logger.info("Initializing Mock detector")
            self.detector = MockDetector(confidence_threshold=conf_thresh)
        else:
            model_path = self.settings.inference.detection.model_path
            logger.info("Initializing RT-DETR detector", path=model_path)
            try:
                self.detector = RTDetrDetector(
                    model_path=model_path,
                    backend=self.backend,
                    confidence_threshold=conf_thresh,
                    classes=classes,
                    input_size=input_size
                )
            except Exception as e:
                logger.error("Failed to initialize RT-DETR, falling back to Mock detector", error=str(e))
                self.detector = MockDetector(confidence_threshold=conf_thresh)

    def detect(self, frame: np.ndarray) -> sv.Detections:
        """Run object detection on a frame."""
        if not self.detector:
            raise InferenceError("Detector not initialized")
            
        try:
            return self.detector.detect(frame)
        except Exception as e:
            logger.error("Inference detection failed", error=str(e))
            raise InferenceError("Detection execution error") from e

    def get_status(self) -> Dict[str, Any]:
        """Return status information for the inference engine."""
        if not self.detector:
            return {"active": False}
            
        info = self.detector.get_model_info()
        return {
            "active": True,
            "backend": self.backend.get_provider_name(),
            "model_info": info
        }
