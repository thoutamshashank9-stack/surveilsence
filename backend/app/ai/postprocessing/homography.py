from typing import List, Tuple, Optional
import numpy as np
from app.core.logging import get_logger

logger = get_logger(__name__)

# Try to import cv2, fallback if not available
try:
    import cv2
except ImportError:
    cv2 = None
    logger.warning("cv2 (OpenCV) not installed. Homography calculations will use simulated fallback.")

class HomographyCalibrator:
    """
    Calibrates and translates 2D pixel coordinates (x, y) to real-world 
    ground-plane Cartesian coordinates in meters (X_world, Y_world) 
    using perspective homography projection.
    """
    def __init__(
        self,
        pixel_points: Optional[List[List[float]]] = None,
        world_points: Optional[List[List[float]]] = None
    ):
        self.H: Optional[np.ndarray] = None
        self.H_inv: Optional[np.ndarray] = None
        
        if pixel_points and world_points:
            self.calibrate(pixel_points, world_points)

    def calibrate(self, pixel_points: List[List[float]], world_points: List[List[float]]) -> bool:
        """
        Computes the 3x3 homography matrix H from 4 coplanar point matches.
        """
        if len(pixel_points) != 4 or len(world_points) != 4:
            logger.error("Calibration requires exactly 4 point matches")
            return False

        if cv2 is None:
            logger.error("OpenCV cv2 is required for homography calibration")
            return False

        try:
            pts_src = np.array(pixel_points, dtype=np.float32)
            pts_dst = np.array(world_points, dtype=np.float32)
            
            # Compute homography H mapping pixel -> world
            self.H = cv2.getPerspectiveTransform(pts_src, pts_dst)
            # Compute inverse H mapping world -> pixel
            self.H_inv = np.linalg.inv(self.H)
            
            logger.info("Homography calibration successful", matrix_H=self.H.tolist())
            return True
        except Exception as e:
            logger.error("Failed to compute homography matrix H", error=str(e))
            self.H = None
            self.H_inv = None
            return False

    def pixel_to_world(self, x: float, y: float) -> Tuple[float, float]:
        """
        Transforms pixel coords (x, y) to ground-plane meters (X, Y).
        """
        if self.H is None:
            # Simulated fallback if not calibrated (rough scaling mapping 1px ~ 0.02m)
            return x * 0.02, y * 0.02

        # Projection multiplication
        pts = np.array([[[x, y]]], dtype=np.float32)
        projected = cv2.perspectiveTransform(pts, self.H)
        return float(projected[0][0][0]), float(projected[0][0][1])

    def world_to_pixel(self, X: float, Y: float) -> Tuple[float, float]:
        """
        Transforms world coords in meters (X, Y) to pixel coords (x, y).
        """
        if self.H_inv is None:
            return X / 0.02, Y / 0.02

        pts = np.array([[[X, Y]]], dtype=np.float32)
        projected = cv2.perspectiveTransform(pts, self.H_inv)
        return float(projected[0][0][0]), float(projected[0][0][1])

    def is_calibrated(self) -> bool:
        return self.H is not None

    def to_dict(self) -> dict:
        if self.H is not None:
            return {"H": self.H.tolist()}
        return {}

    @classmethod
    def from_dict(cls, data: dict) -> "HomographyCalibrator":
        calibrator = cls()
        if "H" in data:
            H = np.array(data["H"], dtype=np.float32)
            calibrator.H = H
            calibrator.H_inv = np.linalg.inv(H)
        return calibrator
