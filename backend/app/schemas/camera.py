from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.models.enums import CameraStatus, CameraType

class CameraZoneSchema(BaseModel):
    name: str
    type: str
    points: List[List[int]]
    direction: Optional[str] = None
    restricted: bool = False

class CameraCreate(BaseModel):
    id: str
    name: str
    source: str
    type: CameraType
    enabled: bool = True
    stream_type: str = "sub"
    fps_cap: int = 30
    zones: List[CameraZoneSchema] = []

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    source: Optional[str] = None
    type: Optional[CameraType] = None
    enabled: Optional[bool] = None
    stream_type: Optional[str] = None
    fps_cap: Optional[int] = None
    zones: Optional[List[CameraZoneSchema]] = None

class CameraResponse(BaseModel):
    id: str
    name: str
    source: str
    type: CameraType
    enabled: bool
    status: CameraStatus
    config_json: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CameraStreamResponse(BaseModel):
    camera_id: str
    active: bool
    fps: float
    mjpeg_url: str
