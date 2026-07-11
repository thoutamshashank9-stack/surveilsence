import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from app.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Lazy import duckdb to keep startup fast
try:
    import duckdb
except ImportError:
    duckdb = None
    logger.warning("duckdb not installed. DuckDB analytics engine will run in simulated mode.")

class DuckDBAnalyticsEngine:
    """
    Vectorized OLAP analytics engine running serverless DuckDB queries 
    directly over partitioned Apache Parquet archival datasets.
    """
    def __init__(self, settings: Settings):
        self.settings = settings
        storage_cfg = getattr(settings, "storage", None)
        self.parquet_dir = getattr(storage_cfg, "parquet_output_dir", "data/parquet") if storage_cfg else "data/parquet"
        self.enabled = (getattr(storage_cfg, "duckdb_enabled", False) and duckdb is not None) if storage_cfg else False
        self.conn = None

        if self.enabled:
            try:
                # Connection to file-backed or in-memory DB
                self.conn = duckdb.connect(database=":memory:")
                # Enforce system resource constraints
                mem_limit = getattr(storage_cfg, "duckdb_memory_limit", "2GB")
                threads = getattr(storage_cfg, "duckdb_threads", 4)
                self.conn.execute(f"SET memory_limit = '{mem_limit}'")
                self.conn.execute(f"SET threads = {threads}")
                logger.info("Initialized DuckDB OLAP engine successfully", memory_limit=mem_limit, threads=threads)
            except Exception as e:
                logger.error("Failed to initialize DuckDB connection, running in simulated fallback", error=str(e))
                self.enabled = False

    def has_archived_data(self, dataset_type: str, camera_id: str, date_str: str) -> bool:
        """
        Helper to check if partitioned Parquet folders exist for target camera and date.
        Format of date_str: YYYY-MM-DD
        Format of folder path: year=YYYY/month=MM/day=DD/camera_id=ID
        """
        if not os.path.exists(self.parquet_dir):
            return False
            
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            year = dt.year
            month = dt.strftime("%m")
            day = dt.strftime("%d")
            
            check_path = os.path.join(
                self.parquet_dir, 
                dataset_type, 
                f"year={year}", 
                f"month={month}", 
                f"day={day}", 
                f"camera_id={camera_id}"
            )
            return os.path.exists(check_path)
        except Exception:
            return False

    async def get_footfall(self, camera_id: str, date_str: str) -> dict:
        """
        Vectorized columnar aggregation of LINE_CROSS events.
        """
        if not self.enabled or not self.has_archived_data("events", camera_id, date_str):
            # Return empty structure, parent query router will merge with SQLite
            return {"total_entries": 0, "total_exits": 0, "hourly_trends": []}

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            year = dt.year
            month = dt.strftime("%m")
            day = dt.strftime("%d")

            parquet_glob = os.path.join(
                self.parquet_dir, 
                "events", 
                f"year={year}", 
                f"month={month}", 
                f"day={day}", 
                f"camera_id={camera_id}", 
                "*.parquet"
            )

            # Columnar vectorized SQL execution via DuckDB
            query = f"""
                SELECT 
                    event_type,
                    COUNT(*) as count,
                    hour(cast(timestamp as timestamp)) as hr
                FROM read_parquet('{parquet_glob}')
                WHERE event_type IN ('LINE_CROSS', 'EventType.LINE_CROSS')
                GROUP BY event_type, hr
            """
            
            res_df = self.conn.execute(query).df()
            
            # Post-process into expected REST format
            total_entries = 0
            total_exits = 0
            hourly_trends = {h: {"hour": h, "entries": 0, "exits": 0} for h in range(24)}

            for _, row in res_df.iterrows():
                # We determine entry/exit using the raw metadata stored in parquet
                # For simplified parsing:
                # If we have real results, parse direction
                pass

            # Since metadata_json is stored as string dict in parquet, we can extract details
            meta_query = f"""
                SELECT 
                    metadata_json,
                    hour(cast(timestamp as timestamp)) as hr
                FROM read_parquet('{parquet_glob}')
            """
            meta_df = self.conn.execute(meta_query).df()
            
            for _, row in meta_df.iterrows():
                try:
                    import ast
                    meta = ast.literal_eval(row["metadata_json"])
                    direction = meta.get("direction", "in")
                    hr = int(row["hr"])
                    if direction == "in":
                        hourly_trends[hr]["entries"] += 1
                        total_entries += 1
                    else:
                        hourly_trends[hr]["exits"] += 1
                        total_exits += 1
                except Exception:
                    # Fallback to simple entries count
                    hr = int(row["hr"])
                    hourly_trends[hr]["entries"] += 1
                    total_entries += 1

            return {
                "total_entries": total_entries,
                "total_exits": total_exits,
                "hourly_trends": list(hourly_trends.values())
            }

        except Exception as e:
            logger.error("DuckDB get_footfall failed", error=str(e))
            return {"total_entries": 0, "total_exits": 0, "hourly_trends": []}

    async def get_dwell_stats(self, camera_id: str, date_str: str) -> dict:
        """
        Vectorized columnar average/max dwell calculation.
        """
        if not self.enabled or not self.has_archived_data("events", camera_id, date_str):
            return {"zones": []}

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            year = dt.year
            month = dt.strftime("%m")
            day = dt.strftime("%d")

            parquet_glob = os.path.join(
                self.parquet_dir, 
                "events", 
                f"year={year}", 
                f"month={month}", 
                f"day={day}", 
                f"camera_id={camera_id}", 
                "*.parquet"
            )

            query = f"""
                SELECT 
                    zone_name,
                    AVG(duration_seconds) as avg_dwell,
                    MAX(duration_seconds) as max_dwell,
                    COUNT(*) as sample_count
                FROM read_parquet('{parquet_glob}')
                WHERE zone_name IS NOT NULL AND duration_seconds IS NOT NULL
                GROUP BY zone_name
            """
            
            res_df = self.conn.execute(query).df()
            
            zones = []
            for _, row in res_df.iterrows():
                zones.append({
                    "zone_name": row["zone_name"],
                    "avg_dwell_seconds": float(row["avg_dwell"]),
                    "max_dwell_seconds": float(row["max_dwell"]),
                    "total_visits": int(row["sample_count"])
                })

            return {"zones": zones}

        except Exception as e:
            logger.error("DuckDB get_dwell_stats failed", error=str(e))
            return {"zones": []}

    async def get_heatmap_data(self, camera_id: str, hours_ago: int) -> dict:
        """
        Vectorized coordinate aggregation for spatial heatmaps.
        """
        if not self.enabled or not os.path.exists(self.parquet_dir):
            return {"points": [], "max_intensity": 0}

        try:
            # Aggregate across recent Parquet files that fall within hours_ago window
            cutoff = datetime.utcnow() - timedelta(hours=hours_ago)
            
            # Build list of matching parquet files
            parquet_glob = os.path.join(self.parquet_dir, "coordinates", "**", "*.parquet")

            query = f"""
                SELECT 
                    round(x, 1) as qx,
                    round(y, 1) as qy,
                    COUNT(*) as count
                FROM read_parquet('{parquet_glob}')
                WHERE cast(timestamp as timestamp) >= '{cutoff.isoformat()}'
                GROUP BY qx, qy
                LIMIT 5000
            """
            
            res_df = self.conn.execute(query).df()
            
            points = []
            max_intensity = 0
            for _, row in res_df.iterrows():
                intensity = int(row["count"])
                max_intensity = max(max_intensity, intensity)
                points.append({
                    "x": float(row["qx"]),
                    "y": float(row["qy"]),
                    "intensity": intensity
                })

            return {"points": points, "max_intensity": max_intensity}

        except Exception as e:
            logger.error("DuckDB get_heatmap_data failed", error=str(e))
            return {"points": [], "max_intensity": 0}
