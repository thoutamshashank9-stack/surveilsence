"""RTMPose ONNX pose estimator — Apache-2.0, commercial-safe."""
from __future__ import annotations
import numpy as np
import onnxruntime as ort
from pathlib import Path
from typing import Optional

# COCO-17 keypoint indices used by concealment rules
NOSE, L_WRIST, R_WRIST, L_HIP, R_HIP = 0, 9, 10, 11, 12
L_SHOULDER, R_SHOULDER = 5, 6

class RTMPoseONNX:
    def __init__(self, onnx_path: str, providers: Optional[list] = None):
        path = Path(onnx_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Pose model missing: {path}. Run: python -m app.services.model_registry ensure pose"
            )
        self.session = ort.InferenceSession(
            str(path),
            providers=providers or ["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [o.name for o in self.session.get_outputs()]

    def preprocess(self, crop_bgr: np.ndarray, size=(192, 256)) -> np.ndarray:
        import cv2
        h, w = size
        img = cv2.resize(crop_bgr, (w, h))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        img = (img - mean) / std
        return img.transpose(2, 0, 1)[None, ...].astype(np.float32)

    def infer(self, crop_bgr: np.ndarray) -> np.ndarray:
        """Returns keypoints [17, 3] = (x, y, score) in crop pixel coords."""
        x = self.preprocess(crop_bgr)
        outs = self.session.run(self.output_names, {self.input_name: x})
        kpts = self._decode(outs, crop_bgr.shape[:2])
        return kpts

    def _decode(self, outs, hw) -> np.ndarray:
        # Example if export already gives [1,17,3] or similar:
        if outs[0].ndim == 3 and outs[0].shape[-1] == 3:
            return outs[0][0]
        # Decode SimCC outputs
        if len(outs) >= 2:
            simcc_x, simcc_y = outs[0][0], outs[1][0] # [17, 64] shape typically
            kpts = []
            for i in range(17):
                px = float(np.argmax(simcc_x[i])) * (hw[1] / simcc_x[i].shape[1])
                py = float(np.argmax(simcc_y[i])) * (hw[0] / simcc_y.shape[1])
                kpts.append([px, py, 1.0])
            return np.array(kpts)
        
        raise RuntimeError(
            f"Unexpected RTMPose outputs: {[o.shape for o in outs]}. "
            "Re-export with MMDeploy ONNX simcc config."
        )

def concealment_score(kpts: np.ndarray) -> float:
    """Heuristic: wrists near torso / hips while person is near shelf ROI."""
    if kpts is None or len(kpts) < 13:
        return 0.0
    def mid(a, b):
        return (kpts[a, :2] + kpts[b, :2]) / 2.0
    torso = mid(L_SHOULDER, R_SHOULDER)
    hip = mid(L_HIP, R_HIP)
    scores = []
    for w in (L_WRIST, R_WRIST):
        if kpts[w, 2] < 0.3:
            continue
        d_torso = np.linalg.norm(kpts[w, :2] - torso)
        d_hip = np.linalg.norm(kpts[w, :2] - hip)
        scores.append(1.0 / (1.0 + min(d_torso, d_hip)))
    return float(np.mean(scores)) if scores else 0.0
