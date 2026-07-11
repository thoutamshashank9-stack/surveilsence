import os
import numpy as np
import onnxruntime as ort
import supervision as sv
from typing import List, Optional

from app.ai.detection.base import DetectorBase, ModelCapabilities
from app.ai.backends.base import InferenceBackendBase
from app.ai.preprocessing.letterbox import prepare_input
from app.core.exceptions import InferenceError
from app.core.logging import get_logger

logger = get_logger(__name__)

class RTDetrDetector(DetectorBase):
    def __init__(
        self,
        model_path: str,
        backend: InferenceBackendBase,
        confidence_threshold: float = 0.35,
        classes: Optional[List[int]] = None,
        input_size: tuple = (640, 640)
    ):
        if not os.path.exists(model_path):
            raise InferenceError(f"Model file not found at {model_path}")
            
        self.model_path = model_path
        self.backend = backend
        self.confidence_threshold = confidence_threshold
        self.classes = classes or [0]  # default person class
        self.input_size = input_size
        
        logger.info("Loading RT-DETR Model...", path=model_path, backend=backend.get_provider_name())
        self.session = self.backend.create_session(model_path)
        logger.info("RT-DETR Model loaded successfully")

    def detect(self, frame: np.ndarray) -> sv.Detections:
        h, w, _ = frame.shape
        
        # Preprocessing: letterbox and normalize
        tensor, scale_info = prepare_input(frame, self.input_size)
        
        inputs = {
            "pixel_values": tensor
        }
        
        try:
            outputs = self.backend.run(self.session, inputs)
            # HF Optimum outputs:
            # logits: [batch, 300, 80]
            # pred_boxes: [batch, 300, 4]
            logits, boxes = outputs[0][0], outputs[1][0]
        except Exception as e:
            logger.error("Inference execution failed", error=str(e))
            raise InferenceError("ONNX Runtime execution failed") from e
            
        # Apply sigmoid to logits to get probabilities
        probs = 1.0 / (1.0 + np.exp(-logits))
        scores = probs.max(axis=-1)
        labels = probs.argmax(axis=-1)
        
        # Convert [cx, cy, w, h] normalized to original [x1, y1, x2, y2] coords
        scale = scale_info["scale"]
        cx, cy, wb, hb = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        
        canvas_x1 = (cx - wb / 2) * self.input_size[0]
        canvas_y1 = (cy - hb / 2) * self.input_size[1]
        canvas_x2 = (cx + wb / 2) * self.input_size[0]
        canvas_y2 = (cy + hb / 2) * self.input_size[1]
        
        x1 = canvas_x1 / scale
        y1 = canvas_y1 / scale
        x2 = canvas_x2 / scale
        y2 = canvas_y2 / scale
        
        converted_boxes = np.stack([x1, y1, x2, y2], axis=-1)
            
        # Postprocessing: Filter by conf and class
        keep = (scores >= self.confidence_threshold)
        
        if self.classes:
            class_mask = np.isin(labels, self.classes)
            keep = keep & class_mask
            
        filtered_boxes = converted_boxes[keep]
        filtered_scores = scores[keep]
        filtered_labels = labels[keep].astype(np.int32)
        
        if len(filtered_boxes) == 0:
            return sv.Detections.empty()
            
        # Supervision Detections expects bounding boxes to be within image limits
        filtered_boxes[:, [0, 2]] = np.clip(filtered_boxes[:, [0, 2]], 0, w)
        filtered_boxes[:, [1, 3]] = np.clip(filtered_boxes[:, [1, 3]], 0, h)
        
        return sv.Detections(
            xyxy=filtered_boxes,
            confidence=filtered_scores,
            class_id=filtered_labels
        )

    def get_model_info(self) -> dict:
        return {
            "model": "rtdetrv2",
            "type": "ONNX",
            "classes": self.classes,
            "input_size": self.input_size,
            "provider": self.backend.get_provider_name()
        }

    def get_capabilities(self) -> ModelCapabilities:
        res = self.input_size[0] if isinstance(self.input_size, (list, tuple)) else self.input_size
        return ModelCapabilities(
            supports_nms_free=False,
            input_resolution=int(res),
            max_batch_size=1
        )

