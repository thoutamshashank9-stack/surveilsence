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

class DoubleLineConfig(BaseModel):
    enabled: bool = False
    line_separation_px: int = 30
    max_crossing_time_seconds: float = 3.0

class CameraZoneConfig(BaseModel):
    name: str
    type: str  # polygon, line
    points: List[List[int]]
    direction: Optional[str] = None  # horizontal, vertical (for line crossing)
    restricted: bool = False
    double_line: DoubleLineConfig = DoubleLineConfig()

class HomographyConfig(BaseModel):
    enabled: bool = False
    pixel_points: List[List[float]] = []
    world_points: List[List[float]] = []

class CameraConfigItem(BaseModel):
    id: str
    name: str
    source: str
    type: str  # file, rtsp, usb, mock
    enabled: bool = True
    stream_type: str = "sub"
    fps_cap: int = 30
    zones: List[CameraZoneConfig] = []
    homography: HomographyConfig = HomographyConfig()

class SAHIConfig(BaseModel):
    enabled: bool = False
    slice_height: int = 640
    slice_width: int = 640
    overlap_ratio: float = 0.2

class DetectionConfig(BaseModel):
    model: str = "rtdetrv2_r18"
    model_path: str = "models/registry/detection/rtdetrv2_r18vd.onnx"
    confidence_threshold: float = 0.35
    input_size: List[int] = [640, 640]
    classes: List[int] = [0]
    max_detections: int = 100
    sahi: SAHIConfig = SAHIConfig()

class ReIDConfig(BaseModel):
    enabled: bool = False
    model_path: str = ""
    embedding_dim: int = 512
    match_threshold: float = 0.6

class CrossCameraConfig(BaseModel):
    enabled: bool = False
    reid: ReIDConfig = ReIDConfig()
    transition_time_seconds: Dict[str, float] = {}

class TrackingConfig(BaseModel):
    algorithm: str = "bytetrack"
    track_activation_threshold: float = 0.25
    lost_track_buffer: int = 30
    minimum_matching_threshold: float = 0.8
    frame_rate: int = 30
    minimum_consecutive_frames: int = 1
    cross_camera: CrossCameraConfig = CrossCameraConfig()

class DirectMLConfig(BaseModel):
    session_per_camera: bool = True
    enable_graph_surgery: bool = True
    max_batch_size: int = 4
    max_wait_ms: float = 10.0

class InferenceConfig(BaseModel):
    backend: str = "auto"
    detection: DetectionConfig = DetectionConfig()
    tracking: TrackingConfig = TrackingConfig()
    directml: DirectMLConfig = DirectMLConfig()

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

class AnalyticsConfig(BaseModel):
    heatmap_resolution: List[int] = [64, 48]
    aggregation_interval_minutes: int = 60
    retention_days: int = 90

class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""

class EmailConfig(BaseModel):
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587

class WhatsAppConfig(BaseModel):
    enabled: bool = False
    provider: str = "twilio"
    api_key: str = ""
    account_sid: str = ""
    auth_token: str = ""
    from_number: str = ""
    to_number: str = ""
    instance_id: str = ""
    token: str = ""

class NotificationConfig(BaseModel):
    telegram: TelegramConfig = TelegramConfig()
    email: EmailConfig = EmailConfig()
    whatsapp: WhatsAppConfig = WhatsAppConfig()

class VLMConfig(BaseModel):
    enabled: bool = False
    backend: str = "simulated"  # simulated | moondream2 | paligemma | ollama
    model: str = "moondream2"
    endpoint: str = "http://localhost:11434"
    timeout_seconds: int = 10

class StorageConfig(BaseModel):
    parquet_enabled: bool = False
    parquet_flush_interval_minutes: int = 5
    parquet_output_dir: str = "data/parquet"
    duckdb_enabled: bool = False
    duckdb_memory_limit: str = "2GB"
    duckdb_threads: int = 4

class SweetheartingRuleConfig(BaseModel):
    enabled: bool = False
    conveyor_zone: str = "conveyor"
    bagging_zone: str = "bagging"
    time_threshold: float = 3.0

class PoseConfig(BaseModel):
    enabled: bool = False
    model_id: str = "rtmpose-t"
    onnx_path: str = "models/registry/pose/rtmpose-t.onnx"
    input_size: List[int] = [256, 192]
    conf_threshold: float = 0.3
    license: str = "Apache-2.0"
    backend: str = "onnxruntime"

class ConcealmentRuleConfig(BaseModel):
    enabled: bool = False
    proximity_threshold: float = 0.3
    pose: PoseConfig = PoseConfig()

class VelocityLoiteringRuleConfig(BaseModel):
    enabled: bool = False
    dwell_threshold_seconds: float = 30.0
    velocity_threshold_mps: float = 0.2

class BehavioralConfig(BaseModel):
    sweethearting: SweetheartingRuleConfig = SweetheartingRuleConfig()
    concealment: ConcealmentRuleConfig = ConcealmentRuleConfig()
    velocity_loitering: VelocityLoiteringRuleConfig = VelocityLoiteringRuleConfig()

class LoRaConfig(BaseModel):
    enabled: bool = False
    frequency: int = 868000000
    spreading_factor: int = 7
    gpio_pins: Dict[str, int] = {}

class FeatureFlags(BaseModel):
    footfall: bool = True
    dwell: bool = True
    heatmaps: bool = True
    queues: bool = True
    employee_bi: bool = True
    pos_conversion: bool = True
    concealment: bool = False      # True only after RTMPose wired + tests pass
    sweethearting: bool = False
    vlm_verify: bool = False
    cross_camera_reid: bool = False

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
    analytics: AnalyticsConfig = AnalyticsConfig()
    notifications: NotificationConfig = NotificationConfig()
    features: FeatureFlags = FeatureFlags()
    vlm: VLMConfig = VLMConfig()
    database: DatabaseConfig = DatabaseConfig()
    logging: LoggingConfig = LoggingConfig()
    storage: StorageConfig = StorageConfig()
    behavioral: BehavioralConfig = BehavioralConfig()
    lora: LoRaConfig = LoRaConfig()
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
