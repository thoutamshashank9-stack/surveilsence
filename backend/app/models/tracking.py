from datetime import datetime
from sqlalchemy import Integer, String, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class TrackSummary(Base):
    __tablename__ = "track_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(Integer, index=True)
    camera_id: Mapped[str] = mapped_column(String(50), ForeignKey("cameras.id"), index=True)
    start_timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    end_timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    role: Mapped[str] = mapped_column(String(50), default="customer") # worker, customer, unknown
    visited_zones_json: Mapped[list] = mapped_column(JSON, default=list) # List of zone names visited
    has_checkout: Mapped[bool] = mapped_column(Boolean, default=False)
    total_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class TrackCoordinate(Base):
    __tablename__ = "track_coordinates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(Integer, index=True)
    camera_id: Mapped[str] = mapped_column(String(50), ForeignKey("cameras.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    zone_name: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
