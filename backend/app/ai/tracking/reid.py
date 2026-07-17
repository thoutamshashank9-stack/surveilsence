"""OSNet-class Re-ID ONNX Embedding Generator — MIT/commercially safe."""
from __future__ import annotations
import numpy as np
import onnxruntime as ort
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

@dataclass
class GalleryEntry:
    emb: np.ndarray
    camera_id: str
    track_id: int
    last_ts: float

class ReIDMatcher:
    def __init__(self, onnx_path: str, dim: int = 512, threshold: float = 0.55, backend: Optional[Any] = None):
        if backend is not None:
            self.session = backend.create_session(onnx_path)
        else:
            self.session = ort.InferenceSession(
                onnx_path,
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
            )
        self.input_name = self.session.get_inputs()[0].name
        self.threshold = threshold
        self.gallery: List[GalleryEntry] = []
        self.global_id_counter = 0
        self.local_to_global: Dict[Tuple[str, int], int] = {}

    def preprocess(self, crop_bgr: np.ndarray) -> np.ndarray:
        import cv2
        img = cv2.resize(crop_bgr, (128, 256))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        img = img.transpose(2, 0, 1)[None, ...]
        return img

    def embed(self, crop_bgr: np.ndarray) -> np.ndarray:
        x = self.preprocess(crop_bgr)
        emb = self.session.run(None, {self.input_name: x})[0][0]
        emb = emb / (np.linalg.norm(emb) + 1e-8)
        return emb.astype(np.float32)

    def assign_global_id(
        self, camera_id: str, track_id: int, crop_bgr: np.ndarray, ts: float
    ) -> int:
        key = (camera_id, track_id)
        if key in self.local_to_global:
            return self.local_to_global[key]

        emb = self.embed(crop_bgr)
        best_id, best_sim = None, -1.0
        for g in self.gallery:
            if g.camera_id == camera_id:
                continue  # same-camera: ByteTrack already owns ID
            sim = float(np.dot(emb, g.emb))
            if sim > best_sim:
                best_sim, best_id = sim, self.local_to_global.get(
                    (g.camera_id, g.track_id)
                )

        if best_sim >= self.threshold and best_id is not None:
            gid = best_id
        else:
            self.global_id_counter += 1
            gid = self.global_id_counter

        self.local_to_global[key] = gid
        self.gallery.append(
            GalleryEntry(emb=emb, camera_id=camera_id, track_id=track_id, last_ts=ts)
        )
        # prune gallery entries older than 10 minutes (600s) to keep search fast
        self.gallery = [g for g in self.gallery if ts - g.last_ts < 600.0]
        return gid
