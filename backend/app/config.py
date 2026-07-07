import os
import sys
from functools import lru_cache
from typing import List, Dict, Any, Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppConfig(BaseModel):
    name: str = "Edge AI CCTV Analytics"
    version: str = "0.1.0"
    debug: bool = True

class CameraZoneConfig(BaseModel):
    name: str
    type: str  # polygon, line
    points: List[List[int]]
    direction: Optional[str] = None  # horizontal, vertical (for line crossing)
    restricted: bool = False

class CameraConfigItem(BaseModel):
    id: str
    name: str
    source: str
    type: str  # file, rtsp, usb, mock
    enabled: bool = True
    stream_type: str = "sub"
    fps_cap: int = 30
    zones: List[CameraZoneConfig] = []

class DetectionConfig(BaseModel):
    model: str = "rtdetrv2_r18"
    model_path: str = "models/registry/detection/rtdetrv2_r18vd.onnx"
    confidence_threshold: float = 0.35
    input_size: List[int] = [640, 640]
    classes: List[int] = [0]
    max_detections: int = 100

class TrackingConfig(BaseModel):
    algorithm: str = "bytetrack"
    track_activation_threshold: float = 0.25
    lost_track_buffer: int = 30
    minimum_matching_threshold: float = 0.8
    frame_rate: int = 30
    minimum_consecutive_frames: int = 1

class InferenceConfig(BaseModel):
    backend: str = "auto"
    detection: DetectionConfig = DetectionConfig()
    tracking: TrackingConfig = TrackingConfig()

class RuleConfig(BaseModel):
    enabled: bool = True
    zones: Optional[List[str]] = None
    lines: Optional[List[str]] = None
    threshold_seconds: Optional[int] = None
    cooldown_seconds: int = 300
    severity: str = "warning"

class AlertConfig(BaseModel):
    intrusion: RuleConfig = RuleConfig(severity="critical")
    loitering: RuleConfig = RuleConfig(threshold_seconds=60, severity="warning")
    line_crossing: RuleConfig = RuleConfig(cooldown_seconds=10, severity="info")
    dwell_no_checkout: RuleConfig = RuleConfig(threshold_seconds=120, severity="warning")

class DatabaseConfig(BaseModel):
    url: str = "sqlite+aiosqlite:///./data/events.db"
    echo: bool = False

class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "console"
    file: Optional[str] = "data/system.log"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore"
    )

    app: AppConfig = AppConfig()
    cameras: List[CameraConfigItem] = []
    inference: InferenceConfig = InferenceConfig()
    alerts: AlertConfig = AlertConfig()
    database: DatabaseConfig = DatabaseConfig()
    logging: LoggingConfig = LoggingConfig()
    config_path: str = Field(default="config/development.yaml", validation_alias="CONFIG_PATH")

@lru_cache()
def get_settings() -> Settings:
    # 1. Instantiate with env vars first
    settings = Settings()
    # 2. Check config YAML
    path = settings.config_path
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                yaml_data = yaml.safe_load(f)
            if yaml_data:
                # Merge dicts
                # Helper to update settings from yaml
                for key, val in yaml_data.items():
                    if hasattr(settings, key):
                        curr = getattr(settings, key)
                        if isinstance(curr, BaseModel) and isinstance(val, dict):
                            # Sub model update
                            setattr(settings, key, curr.__class__(**{**curr.model_dump(), **val}))
                        elif isinstance(curr, list) and isinstance(val, list):
                            # List update
                            if key == "cameras":
                                val = [CameraConfigItem(**item) for item in val]
                            setattr(settings, key, val)
        except Exception as e:
            print(f"Error loading config file {path}: {e}", file=sys.stderr)
    return settings
