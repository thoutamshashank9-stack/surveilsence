"""
Pytest configuration and shared fixtures for the Edge AI CCTV test suite.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session(tmp_path: Path) -> AsyncGenerator[AsyncSession, None]:
    """Create a temporary database session for testing."""
    db_path = tmp_path / "test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
    )

    # Import Base after path setup
    from app.database import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def sample_config() -> dict:
    """Return a sample configuration for testing."""
    return {
        "app": {"name": "Test", "version": "0.1.0", "debug": True},
        "cameras": [
            {
                "id": "test_cam",
                "name": "Test Camera",
                "source": "mock",
                "type": "mock",
                "enabled": True,
                "fps_cap": 10,
                "zones": [],
            }
        ],
        "inference": {
            "backend": "cpu",
            "detection": {
                "model": "mock",
                "confidence_threshold": 0.35,
                "input_size": [640, 640],
                "classes": [0],
                "max_detections": 100,
            },
            "tracking": {
                "algorithm": "bytetrack",
                "track_activation_threshold": 0.25,
                "lost_track_buffer": 30,
                "minimum_matching_threshold": 0.8,
                "frame_rate": 10,
                "minimum_consecutive_frames": 1,
            },
        },
        "database": {"url": "sqlite+aiosqlite:///./data/test.db", "echo": False},
        "logging": {"level": "DEBUG", "format": "console"},
    }
