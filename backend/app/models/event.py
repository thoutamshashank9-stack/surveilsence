from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.enums import EventType

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    camera_id: Mapped[str] = mapped_column(String(50), ForeignKey("cameras.id"), index=True)
    event_type: Mapped[EventType] = mapped_column(String(50), index=True)
    track_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    zone_name: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
