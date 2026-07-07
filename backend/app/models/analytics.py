from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class HourlyAggregate(Base):
    __tablename__ = "hourly_aggregates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(String(50), ForeignKey("cameras.id"), index=True)
    hour_timestamp: Mapped[datetime] = mapped_column(DateTime, index=True) # Normalized to starting hour
    zone_name: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    entry_count: Mapped[int] = mapped_column(Integer, default=0)
    exit_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_dwell_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    max_occupancy: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
