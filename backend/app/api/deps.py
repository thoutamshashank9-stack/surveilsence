from typing import AsyncGenerator
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db
from app.services.camera_manager import CameraManager
from app.services.inference_manager import InferenceManager
from app.services.alert_manager import AlertManager
from app.services.analytics_engine import AnalyticsEngine
from app.core.events import EventBus

def get_app_settings() -> Settings:
    return get_settings()

def get_camera_manager(request: Request) -> CameraManager:
    return request.app.state.camera_manager

def get_inference_manager(request: Request) -> InferenceManager:
    return request.app.state.inference_manager

def get_alert_manager(request: Request) -> AlertManager:
    return request.app.state.alert_manager

def get_analytics_engine(request: Request) -> AnalyticsEngine:
    return request.app.state.analytics_engine

def get_event_bus(request: Request) -> EventBus:
    return request.app.state.event_bus
