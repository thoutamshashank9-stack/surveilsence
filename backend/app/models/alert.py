from datetime import datetime
from sqlalchemy import Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.enums import AlertSeverity, AlertStatus

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    camera_id: Mapped[str] = mapped_column(String(50), ForeignKey("cameras.id"), index=True)
    alert_type: Mapped[str] = mapped_column(String(50), index=True)  # intrusion, loitering, etc.
    severity: Mapped[AlertSeverity] = mapped_column(String(20), default=AlertSeverity.WARNING, index=True)
    status: Mapped[AlertStatus] = mapped_column(String(20), default=AlertStatus.ACTIVE, index=True)
    track_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    zone_name: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[str] = mapped_column(String(100), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
