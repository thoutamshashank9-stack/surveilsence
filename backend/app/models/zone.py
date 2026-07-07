from datetime import datetime
from sqlalchemy import Integer, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.enums import ZoneType

class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(String(50), ForeignKey("cameras.id"), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    type: Mapped[ZoneType] = mapped_column(String(20))  # polygon, line
    points_json: Mapped[list] = mapped_column(JSON)     # [[x, y], ...]
    restricted: Mapped[bool] = mapped_column(Boolean, default=False)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
