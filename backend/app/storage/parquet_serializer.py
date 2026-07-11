import os
import time
import asyncio
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import select, delete
from app.config import Settings
from app.database import AsyncSessionLocal
from app.models.event import Event
from app.models.tracking import TrackCoordinate
from app.core.logging import get_logger

logger = get_logger(__name__)

class ParquetSerializer:
    """
    Background worker that periodically flushes historical SQLite data rows
    and serializes them into highly compressed Apache Parquet files on M.2 NVMe storage.
    Organizes data in Hive-partitioned layouts: year=YYYY/month=MM/day=DD/camera_id=ID.
    """
    def __init__(self, settings: Settings):
        self.settings = settings
        self.interval = settings.storage.parquet_flush_interval_minutes * 60
        self.output_dir = settings.storage.parquet_output_dir
        self.running = False
        self.task: Optional[asyncio.Task] = None

    def start(self):
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self._loop())
            logger.info("ParquetSerializer archiver loop started", interval_s=self.interval, output_dir=self.output_dir)

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            logger.info("ParquetSerializer archiver loop stopped")

    async def _loop(self):
        while self.running:
            try:
                # Wait for the next flush interval
                await asyncio.sleep(self.interval)
                await self.serialize_and_flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in ParquetSerializer loop execution", error=str(e))
                await asyncio.sleep(60.0)

    async def serialize_and_flush(self):
        """
        Queries and archives events and track_coordinates older than 1 hour.
        """
        logger.info("Starting database Parquet archiving sequence")
        cutoff_time = datetime.utcnow() - timedelta(hours=1)

        async with AsyncSessionLocal() as db:
            try:
                # 1. Archive Events
                event_query = select(Event).where(Event.timestamp < cutoff_time)
                result = await db.execute(event_query)
                events = result.scalars().all()

                if events:
                    # Convert to pandas DataFrame
                    event_data = [{
                        "id": e.id,
                        "timestamp": e.timestamp.isoformat(),
                        "camera_id": e.camera_id,
                        "event_type": e.event_type.value if hasattr(e.event_type, "value") else str(e.event_type),
                        "track_id": e.track_id,
                        "zone_name": e.zone_name,
                        "duration_seconds": e.duration_seconds,
                        "metadata_json": str(e.metadata_json or {})
                    } for e in events]
                    
                    df_events = pd.DataFrame(event_data)
                    
                    # Convert timestamp back to datetime for partition formatting
                    df_events["dt"] = pd.to_datetime(df_events["timestamp"])
                    df_events["year"] = df_events["dt"].dt.year
                    df_events["month"] = df_events["dt"].dt.strftime("%m")
                    df_events["day"] = df_events["dt"].dt.strftime("%d")

                    # Write out as partitioned parquet
                    events_dir = os.path.join(self.output_dir, "events")
                    os.makedirs(events_dir, exist_ok=True)
                    
                    df_events.to_parquet(
                        events_dir,
                        partition_cols=["year", "month", "day", "camera_id"],
                        index=False,
                        engine="pyarrow",
                        compression="snappy"
                    )
                    logger.info("Successfully serialized events to Parquet", count=len(events))

                    # Delete from SQLite
                    event_ids = [e.id for e in events]
                    await db.execute(delete(Event).where(Event.id.in_(event_ids)))

                # 2. Archive TrackCoordinates
                coord_query = select(TrackCoordinate).where(TrackCoordinate.timestamp < cutoff_time)
                result_coords = await db.execute(coord_query)
                coords = result_coords.scalars().all()

                if coords:
                    coord_data = [{
                        "id": c.id,
                        "track_id": c.track_id,
                        "camera_id": c.camera_id,
                        "timestamp": c.timestamp.isoformat(),
                        "x": c.x,
                        "y": c.y,
                        "zone_name": c.zone_name
                    } for c in coords]
                    
                    df_coords = pd.DataFrame(coord_data)
                    df_coords["dt"] = pd.to_datetime(df_coords["timestamp"])
                    df_coords["year"] = df_coords["dt"].dt.year
                    df_coords["month"] = df_coords["dt"].dt.strftime("%m")
                    df_coords["day"] = df_coords["dt"].dt.strftime("%d")

                    coords_dir = os.path.join(self.output_dir, "coordinates")
                    os.makedirs(coords_dir, exist_ok=True)
                    
                    df_coords.to_parquet(
                        coords_dir,
                        partition_cols=["year", "month", "day", "camera_id"],
                        index=False,
                        engine="pyarrow",
                        compression="snappy"
                    )
                    logger.info("Successfully serialized coordinates to Parquet", count=len(coords))

                    # Delete from SQLite
                    coord_ids = [c.id for c in coords]
                    await db.execute(delete(TrackCoordinate).where(TrackCoordinate.id.in_(coord_ids)))

                await db.commit()
                logger.info("Completed database Parquet archiving sequence and SQLite vacuum")
            except Exception as e:
                logger.error("Failed to execute database Parquet archiving sequence, rolling back", error=str(e))
                await db.rollback()
