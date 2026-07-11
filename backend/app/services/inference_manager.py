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
        model_path = self.settings.inference.detection.model_path

        # Phase 7: Apply DirectML Graph Surgery for Transformer architectures
        if (
            self.backend.get_provider_name() == "DmlExecutionProvider"
            and self.settings.inference.directml.enable_graph_surgery
            and ("rtdetr" in model_name or "rfdetr" in model_name)
        ):
            from app.ai.backends.onnx_graph_surgery import DirectMLGraphSurgeon
            patched_path = model_path.replace(".onnx", "_patched_dml.onnx")
            model_path = DirectMLGraphSurgeon.patch_model_for_dml(model_path, patched_path)

        # Initialize base detector
        if model_name == "mock":
            logger.info("Initializing Mock detector")
            self.detector = MockDetector(confidence_threshold=conf_thresh)
        elif "yolo" in model_name:
            logger.info("Initializing YOLO detector", model=model_name, path=model_path)
            from app.ai.detection.yolo import YOLODetector
            try:
                self.detector = YOLODetector(
                    backend=self.backend,
                    model_path=model_path,
                    confidence_threshold=conf_thresh,
                    input_size=input_size[0],
                    model_variant=model_name
                )
            except Exception as e:
                logger.error("Failed to initialize YOLO detector, falling back to Mock", error=str(e))
                self.detector = MockDetector(confidence_threshold=conf_thresh)
        elif model_name == "rfdetr_nano":
            logger.info("Initializing RF-DETR Nano detector", path=model_path)
            from app.ai.detection.rfdetr_detector import RFDetrNanoDetector
            try:
                self.detector = RFDetrNanoDetector(
                    backend=self.backend,
                    model_path=model_path,
                    confidence_threshold=conf_thresh,
                    input_size=input_size[0]
                )
            except Exception as e:
                logger.error("Failed to initialize RF-DETR Nano, falling back to Mock", error=str(e))
                self.detector = MockDetector(confidence_threshold=conf_thresh)
        else:
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

        # Wrap in SAHI if configured
        if self.settings.inference.detection.sahi.enabled:
            logger.info("Wrapping detector with SAHI (Slicing Aided Hyper Inference)")
            from app.ai.detection.sahi_wrapper import SAHIDetector
            sahi_cfg = self.settings.inference.detection.sahi
            self.detector = SAHIDetector(
                base_detector=self.detector,
                slice_height=sahi_cfg.slice_height,
                slice_width=sahi_cfg.slice_width,
                overlap_ratio=sahi_cfg.overlap_ratio
            )



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
