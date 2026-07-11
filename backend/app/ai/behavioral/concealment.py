import time
import math
from typing import Dict, List, Tuple, Optional, Any
from app.ai.behavioral.base import BehavioralClassifierBase
from app.core.logging import get_logger

logger = get_logger(__name__)

class ConcealmentClassifier(BehavioralClassifierBase):
    """
    Hand-to-Body Keypoint Concealment Classifier:
    Uses pose skeletons to detect reach-and-tuck motions (wrist approaching hips/shoulders)
    coinciding with the disappearance of a previously tracked product bounding box.
    """
    def __init__(self, proximity_threshold: float = 0.3):
        self.proximity_threshold = proximity_threshold
        # track_id -> List of historical product bounding boxes associated with it
        self.track_products: Dict[int, List[dict]] = {}
        self.last_update: Dict[int, float] = {}

    def update(
        self,
        track_id: int,
        centroid: Tuple[float, float],
        frame_timestamp: float,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Expects kwargs:
            keypoints: Optional[np.ndarray] shape [17, 2] (COCO keypoint sequence)
            product_disappeared: Optional[bool]
        """
        self.last_update[track_id] = frame_timestamp
        keypoints = kwargs.get("keypoints")
        product_disappeared = kwargs.get("product_disappeared", False)

        if keypoints is None:
            return None

        # 1. Compute wrist-to-hip proximity normalized by torso length (shoulder-to-hip)
        # Keypoints: L_shoulder=5, R_shoulder=6, L_wrist=9, R_wrist=10, L_hip=11, R_hip=12
        try:
            # Check confidence if keypoints have 3 dims [x,y,conf], else assume valid
            l_sh = keypoints[5][:2]
            r_sh = keypoints[6][:2]
            l_wr = keypoints[9][:2]
            r_wr = keypoints[10][:2]
            l_hp = keypoints[11][:2]
            r_hp = keypoints[12][:2]

            # Torso scale factor: average shoulder to hip distance
            torso_length = (
                math.sqrt((l_sh[0] - l_hp[0])**2 + (l_sh[1] - l_hp[1])**2) +
                math.sqrt((r_sh[0] - r_hp[0])**2 + (r_sh[1] - r_hp[1])**2)
            ) / 2.0

            if torso_length <= 0:
                return None

            # Compute minimum wrist-to-hip distance
            d_l_wrist_hip = math.sqrt((l_wr[0] - l_hp[0])**2 + (l_wr[1] - l_hp[1])**2)
            d_r_wrist_hip = math.sqrt((r_wr[0] - r_hp[0])**2 + (r_wr[1] - r_hp[1])**2)
            min_dist = min(d_l_wrist_hip, d_r_wrist_hip) / torso_length

            # 2. Trigger concealment anomaly if hands tuck close to hips while product disappears
            if min_dist <= self.proximity_threshold and product_disappeared:
                logger.warn("Item Concealment Behavior Detected!", track_id=track_id)
                return {
                    "event": "CONCEALMENT_DETECTION",
                    "track_id": track_id,
                    "timestamp": frame_timestamp,
                    "description": f"Target P{track_id} reach-and-tuck concealment gesture detected."
                }

        except Exception as e:
            logger.debug("Failed keypoints validation in ConcealmentClassifier", error=str(e))

        return None

    def reset(self) -> None:
        self.track_products.clear()
        self.last_update.clear()

    def cleanup(self, max_age_seconds: float = 60.0) -> None:
        curr_time = time.time()
        for track_id, last_ts in list(self.last_update.items()):
            if curr_time - last_ts > max_age_seconds:
                self.track_products.pop(track_id, None)
                self.last_update.pop(track_id, None)
