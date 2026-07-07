import base64
from typing import List, Tuple, Dict, Any, Optional
import cv2
import numpy as np
import supervision as sv

def frame_to_jpeg(frame: np.ndarray, quality: int = 80) -> bytes:
    """Encode OpenCV image (BGR) to JPEG format bytes."""
    ret, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ret:
        raise ValueError("Failed to encode frame as JPEG")
    return jpeg.tobytes()

def frame_to_base64(frame: np.ndarray, quality: int = 80) -> str:
    """Encode OpenCV frame to base64 JPEG string."""
    jpeg_bytes = frame_to_jpeg(frame, quality)
    return base64.b64encode(jpeg_bytes).decode("utf-8")

def draw_detections(
    frame: np.ndarray,
    detections: sv.Detections,
    labels: Optional[List[str]] = None
) -> np.ndarray:
    """Draw bounding boxes and class labels/IDs on frame."""
    annotated_frame = frame.copy()
    
    # Bounding Box Annotator
    box_annotator = sv.BoxAnnotator(
        thickness=2,
    )
    # Label Annotator
    label_annotator = sv.LabelAnnotator(
        text_thickness=1,
        text_scale=0.5,
    )
    
    annotated_frame = box_annotator.annotate(
        scene=annotated_frame,
        detections=detections
    )
    
    if labels is None and detections.tracker_id is not None:
        labels = [
            f"P{detections.tracker_id[idx]} ({detections.confidence[idx]:.2f})"
            for idx in range(len(detections))
        ]
        
    if labels:
        annotated_frame = label_annotator.annotate(
            scene=annotated_frame,
            detections=detections,
            labels=labels
        )
        
    return annotated_frame

def draw_zones(frame: np.ndarray, zones: List[Any]) -> np.ndarray:
    """Draw zone polygon bounds on frame."""
    annotated_frame = frame.copy()
    for z in zones:
        pts = np.array(z.points if hasattr(z, "points") else z.get("points"), dtype=np.int32)
        z_type = z.type if hasattr(z, "type") else z.get("type")
        color = (0, 0, 255) if (z.restricted if hasattr(z, "restricted") else z.get("restricted", False)) else (0, 255, 0)
        
        if z_type == "line":
            if len(pts) == 2:
                cv2.line(annotated_frame, tuple(pts[0]), tuple(pts[1]), (0, 255, 255), 2)
        else:
            if len(pts) >= 3:
                cv2.polylines(annotated_frame, [pts], True, color, 2)
                
    return annotated_frame
