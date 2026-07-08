from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class HourlyFootfallItem(BaseModel):
    hour: str # HH:00 format
    entries: int
    exits: int

class FootfallMetrics(BaseModel):
    camera_id: str
    date: str
    total_entries: int
    total_exits: int
    hourly_trends: List[HourlyFootfallItem]

class DwellZoneItem(BaseModel):
    zone_name: str
    avg_dwell_seconds: float
    max_dwell_seconds: float
    total_visitor_count: int

class DwellMetrics(BaseModel):
    camera_id: str
    date: str
    zones: List[DwellZoneItem]

class ZoneStatus(BaseModel):
    zone_name: str
    current_occupancy: int
    max_capacity: int
    restricted: bool

class ZoneAnalytics(BaseModel):
    camera_id: str
    timestamp: datetime
    zones: List[ZoneStatus]

class HeatmapPoint(BaseModel):
    x: float
    y: float
    intensity: float

class HeatmapData(BaseModel):
    camera_id: str
    resolution: List[int]
    points: List[HeatmapPoint]

class BusinessAnalytics(BaseModel):
    camera_id: str
    date: str
    conversion_rate: float
    worker_hours: float
    peak_occupancy: Dict[str, int]

class AnalyticsResponse(BaseModel):
    footfall: FootfallMetrics
    dwell: DwellMetrics
    zones: ZoneAnalytics
    business: BusinessAnalytics
