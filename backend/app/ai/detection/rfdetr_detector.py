import os
import time
import numpy as np
import supervision as sv
from app.ai.detection.base import DetectorBase, ModelCapabilities
from app.ai.backends.base import InferenceBackendBase
from app.ai.preprocessing.letterbox import prepare_input
from app.core.logging import get_logger

logger = get_logger(__name__)


class RFDetrNanoDetector(DetectorBase):
    """
    RF-DETR Nano transformer-based detector optimized for low-latency edge deployment.
    Processes input at a fast 384x384 resolution.
    """
    def __init__(
        self,
        backend: InferenceBackendBase,
        model_path: str,
        confidence_threshold: float = 0.35,
        input_size: int = 384
    ):
        self.backend = backend
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.input_size = input_size
        self.is_mock = not os.path.exists(model_path)
        self.session = None

        if self.is_mock:
            logger.warning("RF-DETR ONNX model not found, running in MOCK mode", model_path=model_path)
        else:
            self.session = self.backend.create_session(model_path)

    def detect(self, frame: np.ndarray) -> sv.Detections:
        if self.is_mock:
            return self._detect_mock(frame)

        h, w, _ = frame.shape
        # Prepare input at 384x384
        input_tensor, scale_info = prepare_input(frame, (self.input_size, self.input_size))

        input_name = self.session.get_inputs()[0].name
        outputs = self.backend.run(self.session, {input_name: input_tensor})

        # RF-DETR Nano output format typically matches RT-DETR:
        # Output 0: logits [1, 300, 80]
        # Output 1: boxes [1, 300, 4] (normalized cx, cy, w, h)
        logits = outputs[0][0]  # Shape: [300, 80]
        boxes = outputs[1][0]   # Shape: [300, 4]

        # Apply sigmoid to logits to get confidence scores
        scores = 1 / (1 + np.exp(-logits))
        
        # Get max score and class ID per query
        class_ids = np.argmax(scores, axis=1)
        confidences = np.max(scores, axis=1)

        # Filter by confidence
        keep = confidences >= self.confidence_threshold
        filtered_boxes = boxes[keep]
        filtered_confidences = confidences[keep]
        filtered_class_ids = class_ids[keep]

        if len(filtered_boxes) == 0:
            return sv.Detections.empty()

        # Convert cx, cy, w, h -> xyxy
        cx, cy, bw, bh = filtered_boxes[:, 0], filtered_boxes[:, 1], filtered_boxes[:, 2], filtered_boxes[:, 3]
        x1 = cx - bw / 2
        y1 = cy - bh / 2
        x2 = cx + bw / 2
        y2 = cy + bh / 2

        # Convert back to pixel coordinates relative to 384x384 input resolution
        # Multiply by input_size to map from normalized to input resolution
        xyxy = np.stack([x1, y1, x2, y2], axis=1) * self.input_size

        # Scale coordinates back to original image size
        pad_x, pad_y = scale_info["pad"][0], scale_info["pad"][1]
        scale = scale_info["scale"]

        xyxy[:, [0, 2]] = (xyxy[:, [0, 2]] - pad_x) / scale
        xyxy[:, [1, 3]] = (xyxy[:, [1, 3]] - pad_y) / scale

        # Clip to frame boundary
        xyxy[:, [0, 2]] = np.clip(xyxy[:, [0, 2]], 0, w)
        xyxy[:, [1, 3]] = np.clip(xyxy[:, [1, 3]], 0, h)

        return sv.Detections(
            xyxy=xyxy,
            confidence=filtered_confidences,
            class_id=filtered_class_ids
        )

    def _detect_mock(self, frame: np.ndarray) -> sv.Detections:
        h, w, _ = frame.shape
        t = time.time()
        
        cx = int(w * 0.4 + w * 0.15 * np.cos(t * 0.3))
        cy = int(h * 0.6 + h * 0.15 * np.sin(t * 0.3))
        bw, bh = 70, 130
        
        xyxy = np.array([[cx - bw//2, cy - bh//2, cx + bw//2, cy + bh//2]], dtype=np.float32)
        confidence = np.array([0.76], dtype=np.float32)
        class_id = np.array([0], dtype=np.int32)
        
        return sv.Detections(
            xyxy=xyxy,
            confidence=confidence,
            class_id=class_id
        )

    def get_model_info(self) -> dict:
        return {
            "model": "rfdetr_nano",
            "type": "transformer_detector",
            "classes": ["person", "vehicle", "fire", "smoke", "weapon"],
            "license": "Apache-2.0"
        }

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supports_nms_free=True,
            input_resolution=self.input_size,
            max_batch_size=8
        )
