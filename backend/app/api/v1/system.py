import time
import platform
import onnxruntime as ort
from fastapi import APIRouter, Depends

from app.api.deps import get_app_settings
from app.config import Settings
from app.schemas.common import HealthResponse

router = APIRouter()

START_TIME = time.time()

@router.get("/health", response_model=HealthResponse, summary="Get system health")
async def get_health():
    """Return system health, uptime and application version."""
    return HealthResponse(
        status="healthy",
        uptime=time.time() - START_TIME,
        version="0.1.0"
    )

@router.get("/hardware", summary="Get hardware capabilities")
async def get_hardware(settings: Settings = Depends(get_app_settings)):
    """Return operating system and detected execution backends details."""
    return {
        "os": platform.system(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "onnx_version": ort.__version__,
        "available_providers": ort.get_available_providers(),
        "preferred_backend": settings.inference.backend
    }
