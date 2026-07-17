import onnxruntime as ort
from typing import List
from app.ai.backends.base import InferenceBackendBase
from app.ai.backends.onnx_cpu import ONNXRuntimeCPU
from app.ai.backends.onnx_cuda import ONNXRuntimeCUDA
from app.ai.backends.onnx_directml import ONNXRuntimeDirectML
from app.core.logging import get_logger

logger = get_logger(__name__)

def detect_hardware() -> List[str]:
    """Detect available execution providers in ONNX Runtime."""
    return ort.get_available_providers()

def select_backend(preference: str = "auto") -> InferenceBackendBase:
    """Select the optimal inference backend based on preference and hardware."""
    available = detect_hardware()
    logger.info("Detecting hardware providers", available=available)

    pref_lower = preference.lower()
    
    if pref_lower == "hailo":
        from app.ai.backends.onnx_hailo import HailoInferenceBackend
        backend = HailoInferenceBackend()
        logger.info("Selected HailoRT Hardware Backend")
        return backend
        
    if pref_lower == "tensorrt" or (pref_lower == "auto" and "TensorrtExecutionProvider" in available):
        from app.ai.backends.onnx_tensorrt import TensorRTBackend
        backend = TensorRTBackend()
        if backend.is_available():
            logger.info("Selected TensorRT Backend")
            return backend

    if pref_lower == "cuda" or (pref_lower == "auto" and "CUDAExecutionProvider" in available):
        backend = ONNXRuntimeCUDA()
        if backend.is_available():
            logger.info("Selected CUDA Backend")
            return backend
            
    if pref_lower == "directml" or (pref_lower == "auto" and "DmlExecutionProvider" in available):
        backend = ONNXRuntimeDirectML()
        if backend.is_available():
            logger.info("Selected DirectML Backend")
            return backend

    # CPU Fallback
    logger.info("Selected CPU Backend")
    return ONNXRuntimeCPU()
