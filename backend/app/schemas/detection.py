from typing import List, Optional
from pydantic import BaseModel

class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

class DetectionResult(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    box: BoundingBox

class TrackedObject(BaseModel):
    track_id: int
    class_id: int
    class_name: str
    confidence: float
    box: BoundingBox
    zone_name: Optional[str] = None
    role: str = "customer" # worker, customer

class FrameAnalysis(BaseModel):
    camera_id: str
    timestamp: float
    fps: float
    detections: List[DetectionResult] = []
    tracked_objects: List[TrackedObject] = []
