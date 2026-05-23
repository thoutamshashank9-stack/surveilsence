import sqlite3
import os
import logging
import json

logger = logging.getLogger(__name__)

class DBManager:
    def __init__(self, config: dict):
        db_path = config.get("logging", {}).get("db_path", "data/events.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()
        logger.info(f"SQLite Database initialized at {db_path}")

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL,
                camera_id TEXT,
                track_id INTEGER,
                event_type TEXT,
                zone_name TEXT,
                duration_s REAL,
                metadata TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracks_summary (
                track_id INTEGER,
                camera_id TEXT,
                start_ts REAL,
                end_ts REAL,
                role TEXT,
                has_checkout INTEGER,
                total_duration_s REAL,
                PRIMARY KEY (track_id, camera_id)
            )
        ''')
        self.conn.commit()

    def insert_event(self, ts, camera_id, track_id, event_type, zone_name=None, duration_s=None, metadata=None):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO events (ts, camera_id, track_id, event_type, zone_name, duration_s, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (ts, camera_id, track_id, event_type, zone_name, duration_s, json.dumps(metadata or {})))
        self.conn.commit()

    def upsert_track_summary(self, track_id, camera_id, start_ts, end_ts, role, has_checkout, total_duration_s):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO tracks_summary 
            (track_id, camera_id, start_ts, end_ts, role, has_checkout, total_duration_s)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (track_id, camera_id, start_ts, end_ts, role, int(has_checkout), total_duration_s))
        self.conn.commit()

    def close(self):
        self.conn.close()
