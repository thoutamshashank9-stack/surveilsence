import numpy as np
import supervision as sv
from typing import List
from app.ai.detection.base import DetectorBase, ModelCapabilities
from app.core.logging import get_logger

logger = get_logger(__name__)

class SAHIDetector(DetectorBase):
    """
    Slicing Aided Hyper Inference (SAHI) wrapper for standard object detectors.
    Divides high-resolution input frames into overlapping slices, runs detection 
    on each slice, and merges detections using non-maximum suppression (NMS).
    """
    def __init__(
        self,
        base_detector: DetectorBase,
        slice_height: int = 640,
        slice_width: int = 640,
        overlap_ratio: float = 0.2
    ):
        self.base_detector = base_detector
        self.slice_height = slice_height
        self.slice_width = slice_width
        self.overlap_ratio = overlap_ratio
        logger.info(
            "SAHI Wrapper initialized",
            slice_size=(slice_width, slice_height),
            overlap=overlap_ratio,
            base_model=base_detector.get_model_info()["model"]
        )

    def detect(self, frame: np.ndarray) -> sv.Detections:
        h, w, _ = frame.shape

        # Calculate step size based on overlap
        step_x = int(self.slice_width * (1 - self.overlap_ratio))
        step_y = int(self.slice_height * (1 - self.overlap_ratio))

        # Generate coordinates of all slices
        slice_coords = []
        for y in range(0, h, step_y):
            for x in range(0, w, step_x):
                # Ensure the slice fits inside the frame (clip or shift)
                x_end = min(x + self.slice_width, w)
                y_end = min(y + self.slice_height, h)
                x_start = max(0, x_end - self.slice_width)
                y_start = max(0, y_end - self.slice_height)
                slice_coords.append((x_start, y_start, x_end, y_end))

        # List to collect all detections from each slice
        all_xyxy = []
        all_confidence = []
        all_class_id = []

        for x_start, y_start, x_end, y_end in slice_coords:
            # Crop slice
            crop = frame[y_start:y_end, x_start:x_end]
            
            # Run detection on crop
            detections = self.base_detector.detect(crop)
            
            if len(detections) > 0:
                # Shift coordinates back to absolute frame space
                shifted_xyxy = detections.xyxy.copy()
                shifted_xyxy[:, [0, 2]] += x_start
                shifted_xyxy[:, [1, 3]] += y_start

                all_xyxy.append(shifted_xyxy)
                all_confidence.append(detections.confidence)
                all_class_id.append(detections.class_id)

        if not all_xyxy:
            return sv.Detections.empty()

        # Concatenate all detections
        merged_xyxy = np.concatenate(all_xyxy, axis=0)
        merged_confidence = np.concatenate(all_confidence, axis=0)
        merged_class_id = np.concatenate(all_class_id, axis=0)

        # Build combined Detections object
        merged_detections = sv.Detections(
            xyxy=merged_xyxy,
            confidence=merged_confidence,
            class_id=merged_class_id
        )

        # Apply Global NMS to resolve overlapping detections across slices
        # Default NMS IoU threshold is 0.5
        return merged_detections.with_nms(threshold=0.5)

    def get_model_info(self) -> dict:
        info = self.base_detector.get_model_info().copy()
        info["sahi_wrapped"] = True
        info["slice_size"] = (self.slice_width, self.slice_height)
        return info

    def get_capabilities(self) -> ModelCapabilities:
        base_cap = self.base_detector.get_capabilities()
        # SAHI processing requires sequential tile evaluation, so maximum parallel batch size is 1
        return ModelCapabilities(
            supports_nms_free=False,  # NMS is always required to merge slices
            input_resolution=max(self.slice_width, self.slice_height),
            max_batch_size=1
        )
