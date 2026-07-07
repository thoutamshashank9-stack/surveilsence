from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.enums import AlertSeverity, AlertStatus

class AlertCreate(BaseModel):
    camera_id: str
    alert_type: str
    severity: AlertSeverity
    track_id: Optional[int] = None
    zone_name: Optional[str] = None
    description: Optional[str] = None
    metadata_json: Optional[dict] = None

class AlertAcknowledge(BaseModel):
    acknowledged_by: str
    notes: Optional[str] = None

class AlertResponse(BaseModel):
    id: int
    timestamp: datetime
    camera_id: str
    alert_type: str
    severity: AlertSeverity
    status: AlertStatus
    track_id: Optional[int]
    zone_name: Optional[str]
    description: Optional[str]
    metadata_json: dict
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class AlertFilter(BaseModel):
    camera_id: Optional[str] = None
    severity: Optional[AlertSeverity] = None
    status: Optional[AlertStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
