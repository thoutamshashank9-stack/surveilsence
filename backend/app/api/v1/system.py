import time
import platform
import os
from typing import Literal, List, Optional
import yaml
import onnxruntime as ort
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_app_settings
from app.config import Settings
from app.schemas.common import HealthResponse
from app.core.security import get_current_user

router = APIRouter()

START_TIME = time.time()

# ---------------------------------------------------------------------------
# Schemas for Notifications Configuration
# ---------------------------------------------------------------------------

class TelegramSchema(BaseModel):
    enabled: bool
    bot_token: str
    chat_id: str

class EmailSchema(BaseModel):
    enabled: bool
    smtp_host: str
    smtp_port: int

class WhatsAppSchema(BaseModel):
    enabled: bool
    provider: str
    account_sid: str
    auth_token: str
    from_number: str
    to_number: str
    instance_id: str = ""
    token: str = ""

class NotificationsUpdateSchema(BaseModel):
    telegram: TelegramSchema
    email: EmailSchema
    whatsapp: WhatsAppSchema

# ---------------------------------------------------------------------------
# Schemas for Detection Model Configuration
# ---------------------------------------------------------------------------

ALLOWED_DETECTION_MODELS = ["rtdetrv2_r18", "rfdetr_nano", "mock"]

_MODEL_REGISTRY = {
    "rtdetrv2_r18": {
        "model_path": "models/registry/detection/rtdetrv2_r18vd.onnx",
        "input_size": [640, 640],
        "license": "Apache-2.0",
    },
    "rfdetr_nano": {
        "model_path": "models/registry/detection/rfdetr_nano.onnx",
        "input_size": [384, 384],
        "license": "Apache-2.0",
    },
    "mock": {
        "model_path": "",
        "input_size": [640, 640],
        "license": "N/A",
    },
}

class DetectionModelUpdateSchema(BaseModel):
    model: Literal["rtdetrv2_r18", "rfdetr_nano", "mock"]
    confidence_threshold: float = Field(default=0.35, ge=0.0, le=1.0)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse, summary="Get system health")
async def get_health():
    """Return system health, uptime and application version."""
    return HealthResponse(
        status="healthy",
        uptime=time.time() - START_TIME,
        version="0.1.0"
    )

@router.get("/hardware", summary="Get hardware capabilities")
async def get_hardware(
    settings: Settings = Depends(get_app_settings),
    current_user: dict = Depends(get_current_user)
):
    """Return operating system and detected execution backends details."""
    return {
        "os": platform.system(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "onnx_version": ort.__version__,
        "available_providers": ort.get_available_providers(),
        "preferred_backend": settings.inference.backend
    }

@router.get("/notifications", summary="Get global notification channel configurations")
async def get_notifications(
    settings: Settings = Depends(get_app_settings),
    current_user: dict = Depends(get_current_user)
):
    """Retrieve settings for Telegram, Email, and WhatsApp channels."""
    if not hasattr(settings, "notifications"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification settings not configured"
        )
    return settings.notifications

@router.put("/notifications", summary="Update global notification channel configurations")
async def update_notifications(
    payload: NotificationsUpdateSchema,
    settings: Settings = Depends(get_app_settings),
    current_user: dict = Depends(get_current_user)
):
    """Update settings in-memory and write back to development.yaml file."""
    path = settings.config_path
    
    # 1. Read existing config
    yaml_data = {}
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                yaml_data = yaml.safe_load(f) or {}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read config file: {str(e)}"
            )

    # 2. Update notifications dict
    yaml_data["notifications"] = payload.model_dump()

    # 3. Write back to config file (this triggers uvicorn reload automatically)
    try:
        with open(path, "w") as f:
            yaml.safe_dump(yaml_data, f, default_flow_style=False)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write config file: {str(e)}"
        )

    # 4. Apply to settings in-memory (in case reload is delayed)
    settings.notifications.telegram.enabled = payload.telegram.enabled
    settings.notifications.telegram.bot_token = payload.telegram.bot_token
    settings.notifications.telegram.chat_id = payload.telegram.chat_id
    
    settings.notifications.email.enabled = payload.email.enabled
    settings.notifications.email.smtp_host = payload.email.smtp_host
    settings.notifications.email.smtp_port = payload.email.smtp_port
    
    settings.notifications.whatsapp.enabled = payload.whatsapp.enabled
    settings.notifications.whatsapp.provider = payload.whatsapp.provider
    settings.notifications.whatsapp.account_sid = payload.whatsapp.account_sid
    settings.notifications.whatsapp.auth_token = payload.whatsapp.auth_token
    settings.notifications.whatsapp.from_number = payload.whatsapp.from_number
    settings.notifications.whatsapp.to_number = payload.whatsapp.to_number
    settings.notifications.whatsapp.instance_id = payload.whatsapp.instance_id
    settings.notifications.whatsapp.token = payload.whatsapp.token

    return {"status": "success", "message": "Notification configurations updated successfully"}

class TelegramTestSchema(BaseModel):
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None

@router.post("/notifications/test-telegram", summary="Dispatch a test security warning image to Telegram bot")
async def test_telegram(
    payload: Optional[TelegramTestSchema] = None,
    settings: Settings = Depends(get_app_settings),
    current_user: dict = Depends(get_current_user)
):
    """Dispatches a test security alert snapshot image with warning text to the configured Telegram bot."""
    from app.services.notification_service import NotificationService
    svc = NotificationService(settings)
    token = payload.bot_token if payload else None
    cid = payload.chat_id if payload else None
    try:
        result = await svc.send_test_telegram(bot_token=token, chat_id=cid)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/capabilities", summary="Get system feature flags and capabilities")
async def get_capabilities(
    settings: Settings = Depends(get_app_settings)
):
    """Retrieve active feature flags and capabilities of the platform."""
    return settings.features


@router.get("/detection-model", summary="Get active detection model configuration")
async def get_detection_model(
    settings: Settings = Depends(get_app_settings),
    current_user: dict = Depends(get_current_user)
):
    """Return the currently active detection model and its parameters."""
    det = settings.inference.detection
    model_name = det.model
    license_info = _MODEL_REGISTRY.get(model_name, {}).get("license", "unknown")
    return {
        "model": model_name,
        "model_path": det.model_path,
        "input_size": det.input_size,
        "confidence_threshold": det.confidence_threshold,
        "license": license_info,
    }


@router.put("/detection-model", summary="Switch the active detection model at runtime")
async def update_detection_model(
    payload: DetectionModelUpdateSchema,
    settings: Settings = Depends(get_app_settings),
    current_user: dict = Depends(get_current_user)
):
    """Switch the detection model, update in-memory settings and persist to YAML."""
    model_name = payload.model

    if model_name not in ALLOWED_DETECTION_MODELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Model '{model_name}' is not allowed. Choose from: {ALLOWED_DETECTION_MODELS}",
        )

    registry_entry = _MODEL_REGISTRY[model_name]

    # 1. Update in-memory settings
    settings.inference.detection.model = model_name
    settings.inference.detection.model_path = registry_entry["model_path"]
    settings.inference.detection.input_size = registry_entry["input_size"]
    settings.inference.detection.confidence_threshold = payload.confidence_threshold

    # 2. Persist to YAML config file
    path = settings.config_path
    yaml_data = {}
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                yaml_data = yaml.safe_load(f) or {}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read config file: {str(e)}",
            )

    # Merge detection block into the inference section
    yaml_data.setdefault("inference", {})
    yaml_data["inference"]["detection"] = {
        "model": model_name,
        "model_path": registry_entry["model_path"],
        "input_size": registry_entry["input_size"],
        "confidence_threshold": payload.confidence_threshold,
    }

    try:
        with open(path, "w") as f:
            yaml.safe_dump(yaml_data, f, default_flow_style=False)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write config file: {str(e)}",
        )

    return {
        "status": "success",
        "active_model": model_name,
        "message": f"Detection model switched to '{model_name}' with confidence {payload.confidence_threshold}",
    }
