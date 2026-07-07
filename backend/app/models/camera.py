from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.enums import CameraStatus, CameraType

class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[CameraType] = mapped_column(String(20), default=CameraType.MOCK)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[CameraStatus] = mapped_column(String(20), default=CameraStatus.OFFLINE)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
