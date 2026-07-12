import time
import platform
import os
import yaml
import onnxruntime as ort
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

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
