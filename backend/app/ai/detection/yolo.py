import os
import numpy as np
import supervision as sv
from app.ai.detection.base import DetectorBase, ModelCapabilities
from app.ai.backends.base import InferenceBackendBase
from app.ai.preprocessing.letterbox import prepare_input
from app.core.logging import get_logger

logger = get_logger(__name__)

class YOLODetector(DetectorBase):
    """
    Unified detector for YOLO11 and YOLO26 ONNX models.
    YOLO26 is end-to-end NMS-free, whereas YOLO11 requires NMS post-processing.
    """
    def __init__(
        self,
        backend: InferenceBackendBase,
        model_path: str,
        confidence_threshold: float = 0.35,
        input_size: int = 640,
        model_variant: str = "yolo26n"
    ):
        self.backend = backend
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.input_size = input_size
        self.model_variant = model_variant
        self.is_mock = not os.path.exists(model_path)
        self.session = None

        if self.is_mock:
            logger.warning(
                "YOLO ONNX model not found, running in MOCK mode",
                model_path=model_path,
                variant=model_variant
            )
        else:
            self.session = self.backend.create_session(model_path)

    def detect(self, frame: np.ndarray) -> sv.Detections:
        if self.is_mock:
            return self._detect_mock(frame)

        h, w, _ = frame.shape
        # Prepare input
        input_tensor, scale_info = prepare_input(frame, (self.input_size, self.input_size))

        # Session inputs
        input_name = self.session.get_inputs()[0].name
        outputs = self.backend.run(self.session, {input_name: input_tensor})

        # Parse outputs
        if self.model_variant == "yolo26n":
            # YOLO26 NMS-free format: typically [1, 300, 6] (boxes, scores, classes)
            # or [1, num_detections, 6] where last dim is [x1, y1, x2, y2, score, class]
            preds = outputs[0][0]  # Shape: [300, 6]
            
            # Filter by confidence threshold
            keep = preds[:, 4] >= self.confidence_threshold
            filtered_preds = preds[keep]

            if len(filtered_preds) == 0:
                return sv.Detections.empty()

            xyxy = filtered_preds[:, :4]
            confidence = filtered_preds[:, 4]
            class_id = filtered_preds[:, 5].astype(np.int32)
        else:
            # YOLO11 (YOLOv8-like) format: [1, 84, 8400] (box center x, center y, w, h, classes...)
            # We need to transpose, scale, convert to xyxy, and apply NMS.
            preds = outputs[0][0]  # Shape: [84, 8400]
            preds = np.transpose(preds)  # Shape: [8400, 84]

            # Box coordinates: x_center, y_center, width, height
            boxes = preds[:, :4]
            # Convert to xyxy
            x1 = boxes[:, 0] - boxes[:, 2] / 2
            y1 = boxes[:, 1] - boxes[:, 3] / 2
            x2 = boxes[:, 0] + boxes[:, 2] / 2
            y2 = boxes[:, 1] + boxes[:, 3] / 2
            xyxy_raw = np.stack([x1, y1, x2, y2], axis=1)

            # Scores are in columns 4 onwards
            scores = preds[:, 4:]
            class_ids_raw = np.argmax(scores, axis=1)
            confidences_raw = np.max(scores, axis=1)

            # Filter by confidence threshold
            keep = confidences_raw >= self.confidence_threshold
            xyxy = xyxy_raw[keep]
            confidence = confidences_raw[keep]
            class_id = class_ids_raw[keep]

            if len(xyxy) == 0:
                return sv.Detections.empty()

            # Apply NMS via supervision to deduplicate
            detections = sv.Detections(
                xyxy=xyxy,
                confidence=confidence,
                class_id=class_id
            )
            return detections.with_nms(threshold=0.5)

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
            confidence=confidence,
            class_id=class_id
        )

    def _detect_mock(self, frame: np.ndarray) -> sv.Detections:
        # Mock detection simulation
        h, w, _ = frame.shape
        t = time.time()
        
        cx = int(w * 0.5 + w * 0.2 * np.sin(t * 0.2))
        cy = int(h * 0.5 + h * 0.2 * np.cos(t * 0.2))
        bw, bh = 80, 150
        
        xyxy = np.array([[cx - bw//2, cy - bh//2, cx + bw//2, cy + bh//2]], dtype=np.float32)
        confidence = np.array([0.89], dtype=np.float32)
        class_id = np.array([0], dtype=np.int32)  # person
        
        return sv.Detections(
            xyxy=xyxy,
            confidence=confidence,
            class_id=class_id
        )

    def get_model_info(self) -> dict:
        return {
            "model": self.model_variant,
            "type": "yolo_detector",
            "classes": ["person", "vehicle", "fire", "smoke", "weapon"],
            "nms_free": self.model_variant == "yolo26n",
            "license": "AGPL-3.0 / Commercial"
        }

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supports_nms_free=self.model_variant == "yolo26n",
            input_resolution=self.input_size,
            max_batch_size=8
        )
