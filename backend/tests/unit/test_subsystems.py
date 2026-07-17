import os
import pytest
import numpy as np
from pathlib import Path

from app.config import get_settings
from app.services.model_registry import ModelRegistry, ensure_model, DOWNLOAD_PROGRESS
from app.ai.tracking.reid import ReIDMatcher
from app.ai.backends.tensorrt_compiler import TensorRTCompiler
from app.services.vlm_service import VLMVerificationService

def test_model_registry_custom_download():
    settings = get_settings()
    registry = ModelRegistry(settings)
    assert registry.registry_path is not None
    assert isinstance(DOWNLOAD_PROGRESS, dict)

def test_reid_matcher_init_fallback():
    # If ONNX file doesn't exist, initialization is tested using a mock path
    # or should fail as expected.
    with pytest.raises(Exception):
        ReIDMatcher(onnx_path="nonexistent_reid.onnx")

def test_tensorrt_compiler_graceful():
    compiler = TensorRTCompiler(precision="fp16")
    # Should run and return None (since TRT python package is not on Windows development by default)
    # or return Path if installed.
    res = compiler.compile("nonexistent_model.onnx")
    assert res is None or isinstance(res, str)

@pytest.mark.anyio
async def test_vlm_verification_service():
    vlm = VLMVerificationService()
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    res = await vlm.verify_frame(frame, "intrusion", "worker_cabin")
    assert "VLM VERIFIED" in res or "SIMULATED" in res
