import cv2
import numpy as np
from typing import Tuple, Dict, Any

def letterbox(
    image: np.ndarray,
    target_size: Tuple[int, int] = (640, 640),
    color: Tuple[int, int, int] = (114, 114, 114)
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Resize image with aspect ratio preservation and padding."""
    ih, iw = image.shape[:2]
    tw, th = target_size
    
    scale = min(tw / iw, th / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    
    resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)
    
    # Create target canvas and copy resized image in center or top-left
    # Typically top-left padding or centered. Let's do top-left to keep scaling math simple
    canvas = np.full((th, tw, 3), color, dtype=np.uint8)
    canvas[0:nh, 0:nw] = resized
    
    scale_info = {
        "scale": scale,
        "pad_w": tw - nw,
        "pad_h": th - nh,
        "orig_w": iw,
        "orig_h": ih
    }
    
    return canvas, scale_info

def normalize(image: np.ndarray) -> np.ndarray:
    """Normalize image from uint8 [0, 255] to float32 [0.0, 1.0] and swap HWC->CHW."""
    # Convert to float32 and rescale
    img_float = image.astype(np.float32) / 255.0
    # HWC to CHW
    img_chw = np.transpose(img_float, (2, 0, 1))
    return img_chw

def prepare_input(image: np.ndarray, target_size: Tuple[int, int] = (640, 640)) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Preprocess raw image to NCHW input tensor."""
    # 1. Letterbox resize
    padded, scale_info = letterbox(image, target_size)
    # 2. Normalize and HWC -> CHW
    chw = normalize(padded)
    # 3. Add batch dimension (CHW -> NCHW)
    nchw = np.expand_dims(chw, axis=0)
    return nchw, scale_info
