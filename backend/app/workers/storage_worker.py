import asyncio
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database import AsyncSessionLocal
from app.core.events import EventBus
from app.models.enums import EventType, AlertStatus
from app.models.event import Event
from app.models.alert import Alert
from app.models.tracking import TrackSummary, TrackCoordinate
from app.core.logging import get_logger

logger = get_logger(__name__)

class StorageWorker:
    def __init__(self, settings: Settings, event_bus: EventBus):
        self.settings = settings
        self.event_bus = event_bus
        from app.services.notification_service import NotificationService
        self.notification_service = NotificationService(settings)
        
        self.event_buffer: List[Dict[str, Any]] = []
        self.alert_buffer: List[Dict[str, Any]] = []
        self.coord_buffer: List[Dict[str, Any]] = []
        
        self.lock = asyncio.Lock()
        self.running = False
        self.flush_interval = 1.5  # Flush every 1.5 seconds
        self.flush_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self.running:
            return
        self.running = True
        
        # Subscribe to Event Bus events
        self.event_bus.subscribe(EventType.ZONE_ENTRY, self.queue_event)
        self.event_bus.subscribe(EventType.ZONE_EXIT, self.queue_event)
        self.event_bus.subscribe(EventType.LINE_CROSS, self.queue_event)
        self.event_bus.subscribe(EventType.DETECTION, self.queue_coordinates)
        self.event_bus.subscribe(EventType.ALERT, self.queue_alert)
        
        self.flush_task = asyncio.create_task(self._flush_loop())
        logger.info("Storage worker started")

    async def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass
        # Perform final flush
        await self.flush()
        logger.info("Storage worker stopped")

    async def queue_event(self, data: Dict[str, Any]) -> None:
        async with self.lock:
            # Map event payload back to DB Event schema
            # Payloads have: camera_id, track_id, zone_name/line_name, timestamp, duration_seconds/direction etc
            event_type = EventType.ZONE_ENTRY
            meta = {}
            if "global_person_id" in data:
                meta["global_person_id"] = data.get("global_person_id")

            if "line_name" in data:
                event_type = EventType.LINE_CROSS
                zone = data.get("line_name")
                meta["direction"] = data.get("direction")
                dur = None
            elif "duration_seconds" in data:
                event_type = EventType.ZONE_EXIT
                zone = data.get("zone_name")
                dur = data.get("duration_seconds")
            else:
                event_type = EventType.ZONE_ENTRY
                zone = data.get("zone_name")
                dur = None

            self.event_buffer.append({
                "timestamp": datetime.fromtimestamp(data.get("timestamp", time.time())),
                "camera_id": data.get("camera_id"),
                "event_type": event_type,
                "track_id": data.get("track_id"),
                "zone_name": zone,
                "duration_seconds": dur,
                "metadata_json": meta
            })

    async def queue_coordinates(self, data: Dict[str, Any]) -> None:
        """Store track coordinate history for heatmaps."""
        async with self.lock:
            camera_id = data.get("camera_id")
            ts = datetime.fromtimestamp(data.get("timestamp", time.time()))
            
            for obj in data.get("tracked_objects", []):
                box = obj.get("box", {})
                # Anchor bottom center
                bx = (box.get("x1", 0) + box.get("x2", 0)) / 2
                by = box.get("y2", 0)
                
                self.coord_buffer.append({
                    "track_id": obj.get("track_id"),
                    "camera_id": camera_id,
                    "timestamp": ts,
                    "x": bx,
                    "y": by,
                    "zone_name": obj.get("zone_name")
                })

    async def queue_alert(self, data: Dict[str, Any]) -> None:
        async with self.lock:
            self.alert_buffer.append({
                "timestamp": datetime.fromtimestamp(data.get("timestamp", time.time())),
                "camera_id": data.get("camera_id"),
                "alert_type": data.get("alert_type"),
                "severity": data.get("severity"),
                "status": AlertStatus.ACTIVE,
                "track_id": data.get("track_id"),
                "zone_name": data.get("zone_name"),
                "description": data.get("description"),
                "metadata_json": data.get("metadata_json", {})
            })

    async def _flush_loop(self) -> None:
        while self.running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in storage worker flush loop", error=str(e))

    async def flush(self) -> None:
        async with self.lock:
            events_to_write = self.event_buffer.copy()
            coords_to_write = self.coord_buffer.copy()
            alerts_to_write = self.alert_buffer.copy()
            
            self.event_buffer.clear()
            self.coord_buffer.clear()
            self.alert_buffer.clear()

        if not events_to_write and not coords_to_write and not alerts_to_write:
            return

        async with AsyncSessionLocal() as db:
            try:
                # 1. Write events
                for e_data in events_to_write:
                    # Update Track Summary lifecycle if exit/entry
                    db.add(Event(**e_data))
                    await self._update_track_summary(db, e_data)
                    
                # 2. Write coordinates
                for c_data in coords_to_write:
                    db.add(TrackCoordinate(**c_data))
                    
                # 3. Write alerts
                for a_data in alerts_to_write:
                    db.add(Alert(**a_data))
                    asyncio.create_task(self.notification_service.send_alert_notification(a_data))
                    
                await db.commit()
                logger.debug("Database buffer flushed successfully", 
                             events=len(events_to_write), 
                             coords=len(coords_to_write), 
                             alerts=len(alerts_to_write))
            except Exception as e:
                logger.error("Failed to commit flush to database, rolling back", error=str(e))
                await db.rollback()

    async def _update_track_summary(self, db: AsyncSession, event_data: Dict[str, Any]) -> None:
        """Maintain the track_summaries time-series lifecycle state."""
        track_id = event_data.get("track_id")
        camera_id = event_data.get("camera_id")
        ts = event_data.get("timestamp")
        event_type = event_data.get("event_type")
        zone = event_data.get("zone_name")
        
        if not track_id:
            return

        # Check if TrackSummary exists
        q = select(TrackSummary).where(
            and_(TrackSummary.track_id == track_id, TrackSummary.camera_id == camera_id)
        )
        res = await db.execute(q)
        summary = res.scalar_one_or_none()
        
        if not summary:
            # Create new summary record
            summary = TrackSummary(
                track_id=track_id,
                camera_id=camera_id,
                start_timestamp=ts,
                end_timestamp=ts,
                visited_zones_json=[zone] if zone else [],
                has_checkout=(zone == "checkout"),
                total_duration_seconds=0.0
            )
            db.add(summary)
        else:
            # Update summary
            summary.end_timestamp = ts
            
            # Check duration
            diff = (ts - summary.start_timestamp).total_seconds()
            summary.total_duration_seconds = max(0.0, diff)
            
            # Append zone if not in list
            if zone:
                zones = list(summary.visited_zones_json)
                if zone not in zones:
                    zones.append(zone)
                    summary.visited_zones_json = zones
                    
            if zone == "checkout":
                summary.has_checkout = True
                
            # Classify worker vs customer
            # If spent > settings threshold in worker_cabin or restricted zone, mark as worker
            if zone == "worker_cabin" and summary.total_duration_seconds > 60:
                summary.role = "worker"
