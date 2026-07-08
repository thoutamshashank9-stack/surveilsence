from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.event import Event
from app.models.tracking import TrackSummary, TrackCoordinate
from app.models.enums import EventType
from app.schemas.analytics import (
    FootfallMetrics, HourlyFootfallItem, DwellMetrics, DwellZoneItem, 
    ZoneAnalytics, ZoneStatus, HeatmapData, HeatmapPoint
)
from app.core.logging import get_logger

logger = get_logger(__name__)

class AnalyticsEngine:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def get_footfall(self, db: AsyncSession, camera_id: str, date_str: str) -> FootfallMetrics:
        """Query entries and exits hourly for a camera on a specific date."""
        try:
            start_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
        end_date = start_date + timedelta(days=1)
        
        # Query total entries and exits
        # Note: Line crossing triggers an entry or exit event.
        # We query the SQLite database events table
        query_in = select(func.count()).where(
            and_(
                Event.camera_id == camera_id,
                Event.event_type == EventType.LINE_CROSS,
                Event.metadata_json["direction"].as_string() == "in",
                Event.timestamp >= start_date,
                Event.timestamp < end_date
            )
        )
        query_out = select(func.count()).where(
            and_(
                Event.camera_id == camera_id,
                Event.event_type == EventType.LINE_CROSS,
                Event.metadata_json["direction"].as_string() == "out",
                Event.timestamp >= start_date,
                Event.timestamp < end_date
            )
        )
        
        total_in = (await db.execute(query_in)).scalar() or 0
        total_out = (await db.execute(query_out)).scalar() or 0
        
        # Query hourly trends
        hourly_trends: List[HourlyFootfallItem] = []
        for hour in range(24):
            hour_start = start_date + timedelta(hours=hour)
            hour_end = hour_start + timedelta(hours=1)
            
            q_hour_in = select(func.count()).where(
                and_(
                    Event.camera_id == camera_id,
                    Event.event_type == EventType.LINE_CROSS,
                    Event.metadata_json["direction"].as_string() == "in",
                    Event.timestamp >= hour_start,
                    Event.timestamp < hour_end
                )
            )
            q_hour_out = select(func.count()).where(
                and_(
                    Event.camera_id == camera_id,
                    Event.event_type == EventType.LINE_CROSS,
                    Event.metadata_json["direction"].as_string() == "out",
                    Event.timestamp >= hour_start,
                    Event.timestamp < hour_end
                )
            )
            
            h_in = (await db.execute(q_hour_in)).scalar() or 0
            h_out = (await db.execute(q_hour_out)).scalar() or 0
            
            hourly_trends.append(HourlyFootfallItem(
                hour=f"{hour:02d}:00",
                entries=h_in,
                exits=h_out
            ))
            
        return FootfallMetrics(
            camera_id=camera_id,
            date=start_date.strftime("%Y-%m-%d"),
            total_entries=total_in,
            total_exits=total_out,
            hourly_trends=hourly_trends
        )

    async def get_dwell_stats(self, db: AsyncSession, camera_id: str, date_str: str) -> DwellMetrics:
        """Query dwell time per zone for a specific date."""
        try:
            start_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
        end_date = start_date + timedelta(days=1)
        
        # Query distinct zones from events in time range
        q_zones = select(Event.zone_name).where(
            and_(
                Event.camera_id == camera_id,
                Event.zone_name.isnot(None),
                Event.timestamp >= start_date,
                Event.timestamp < end_date
            )
        ).distinct()
        
        zones_res = await db.execute(q_zones)
        zone_names = [r[0] for r in zones_res.fetchall()]
        
        zones_data: List[DwellZoneItem] = []
        for zone in zone_names:
            # Query dwell time duration from DWELL_END events
            q_dwell = select(
                func.avg(Event.duration_seconds),
                func.max(Event.duration_seconds),
                func.count(func.distinct(Event.track_id))
            ).where(
                and_(
                    Event.camera_id == camera_id,
                    Event.event_type == EventType.ZONE_EXIT,
                    Event.zone_name == zone,
                    Event.timestamp >= start_date,
                    Event.timestamp < end_date
                )
            )
            
            res = (await db.execute(q_dwell)).fetchone()
            if res and res[2] > 0:
                zones_data.append(DwellZoneItem(
                    zone_name=zone,
                    avg_dwell_seconds=round(res[0] or 0.0, 1),
                    max_dwell_seconds=round(res[1] or 0.0, 1),
                    total_visitor_count=res[2]
                ))
                
        return DwellMetrics(
            camera_id=camera_id,
            date=start_date.strftime("%Y-%m-%d"),
            zones=zones_data
        )

    async def get_zone_analytics(self, db: AsyncSession, camera_id: str) -> ZoneAnalytics:
        """Get real-time zone occupancy status."""
        # Find camera config to get maximum capacity/restricted
        zones_status: List[ZoneStatus] = []
        
        # Get camera config zones
        cam_zones = []
        for cam_cfg in self.settings.cameras:
            if cam_cfg.id == camera_id:
                cam_zones = cam_cfg.zones
                break
                
        for zone in cam_zones:
            # Current occupancy: count active tracks in zone in last 10 seconds
            # An active track has coordinate in track_coordinates in the last 10 seconds
            cutoff = datetime.utcnow() - timedelta(seconds=10)
            
            q_occ = select(func.count(func.distinct(TrackCoordinate.track_id))).where(
                and_(
                    TrackCoordinate.camera_id == camera_id,
                    TrackCoordinate.zone_name == zone.name,
                    TrackCoordinate.timestamp >= cutoff
                )
            )
            
            occupancy = (await db.execute(q_occ)).scalar() or 0
            
            zones_status.append(ZoneStatus(
                zone_name=zone.name,
                current_occupancy=occupancy,
                max_capacity=10,  # Default threshold placeholder
                restricted=zone.restricted
            ))
            
        return ZoneAnalytics(
            camera_id=camera_id,
            timestamp=datetime.utcnow(),
            zones=zones_status
        )

    async def get_heatmap_data(self, db: AsyncSession, camera_id: str, hours_ago: int = 24) -> HeatmapData:
        """Query coordinate list to build heatmaps."""
        cutoff = datetime.utcnow() - timedelta(hours=hours_ago)
        
        q_coords = select(TrackCoordinate.x, TrackCoordinate.y).where(
            and_(
                TrackCoordinate.camera_id == camera_id,
                TrackCoordinate.timestamp >= cutoff
            )
        ).limit(10000) # Limit count to protect memory
        
        res = await db.execute(q_coords)
        points_list: List[HeatmapPoint] = []
        
        # Quantize points into grid coordinates to reduce payload size
        # Grid layout: 64x48
        grid: Dict[Tuple[int, int], int] = {}
        for r in res.fetchall():
            gx = int(r[0] / 10)  # Group by 10 pixels
            gy = int(r[1] / 10)
            grid[(gx, gy)] = grid.get((gx, gy), 0) + 1
            
        if grid:
            max_val = max(grid.values())
            for (gx, gy), count in grid.items():
                points_list.append(HeatmapPoint(
                    x=float(gx * 10),
                    y=float(gy * 10),
                    intensity=count / max_val
                ))
                
        return HeatmapData(
            camera_id=camera_id,
            resolution=self.settings.analytics.heatmap_resolution,
            points=points_list
        )
