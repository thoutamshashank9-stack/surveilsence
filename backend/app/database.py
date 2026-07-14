import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event

from app.config import get_settings

settings = get_settings()

# Create SQLite parent folder if it doesn't exist
if settings.database.url.startswith("sqlite"):
    # url is sqlite+aiosqlite:///./data/events.db
    db_path = settings.database.url.split("///")[-1]
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

engine = create_async_engine(
    settings.database.url,
    echo=settings.database.echo,
    connect_args={"check_same_thread": False, "timeout": 30.0} if "sqlite" in settings.database.url else {}
)

# Enable WAL mode for SQLite
if "sqlite" in settings.database.url:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db() -> None:
    # Import all models to ensure they are registered on DeclarativeBase
    from app.models.camera import Camera
    from app.models.event import Event
    from app.models.alert import Alert
    from app.models.zone import Zone
    from app.models.tracking import TrackSummary, TrackCoordinate
    from app.models.analytics import HourlyAggregate
    from app.models.employee_analytics import StaffShift, StaffInteraction

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

