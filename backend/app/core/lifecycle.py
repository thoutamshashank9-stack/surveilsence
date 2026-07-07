import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
import onnxruntime as ort

from app.config import get_settings
from app.database import init_db
from app.core.logging import setup_logging, get_logger
from app.core.events import EventBus
from app.services.camera_manager import CameraManager
from app.services.inference_manager import InferenceManager
from app.services.tracking_manager import TrackingManager
from app.services.alert_manager import AlertManager
from app.services.analytics_engine import AnalyticsEngine
from app.workers.storage_worker import StorageWorker
from app.workers.camera_worker import CameraWorker
from app.api.websocket.manager import ConnectionManager
from app.api.websocket.events import EventBroadcaster

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    
    # 1. Setup Logging
    setup_logging(
        log_level=settings.logging.level,
        log_format=settings.logging.format,
        log_file=settings.logging.file
    )
    
    logger.info("Initializing Edge AI CCTV Analytics Platform...")
    start_time = time.time()
    
    # 2. Init Database
    await init_db()
    logger.info("Database initialized successfully")
    
    # 3. Create Event Bus
    event_bus = EventBus()
    await event_bus.start()
    app.state.event_bus = event_bus
    
    # 4. Instantiate Singletons
    # Camera Manager
    camera_manager = CameraManager(settings, event_bus)
    app.state.camera_manager = camera_manager
    
    # Inference Manager
    inference_manager = InferenceManager(settings)
    app.state.inference_manager = inference_manager
    
    # Tracking Manager
    tracking_manager = TrackingManager(settings)
    app.state.tracking_manager = tracking_manager
    
    # Alert Manager
    alert_manager = AlertManager(settings)
    app.state.alert_manager = alert_manager
    
    # Analytics Engine
    analytics_engine = AnalyticsEngine(settings)
    app.state.analytics_engine = analytics_engine
    
    # WebSocket Connection Manager & Broadcaster
    websocket_manager = ConnectionManager()
    app.state.websocket_manager = websocket_manager
    
    event_broadcaster = EventBroadcaster(event_bus, websocket_manager)
    event_broadcaster.start()
    app.state.event_broadcaster = event_broadcaster
    
    # Storage Worker (acts as event subscriber to database write queue)
    storage_worker = StorageWorker(settings, event_bus)
    await storage_worker.start()
    app.state.storage_worker = storage_worker
    app.state.camera_workers = {}
    
    # 5. Load and initialize cameras from config
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.camera import Camera
    from app.models.enums import CameraStatus
    
    async with AsyncSessionLocal() as db:
        for cam_config in settings.cameras:
            q = select(Camera).where(Camera.id == cam_config.id)
            res = await db.execute(q)
            existing = res.scalar_one_or_none()
            
            if not existing:
                db_cam = Camera(
                    id=cam_config.id,
                    name=cam_config.name,
                    source=cam_config.source,
                    type=cam_config.type,
                    enabled=cam_config.enabled,
                    status=CameraStatus.ONLINE if cam_config.enabled else CameraStatus.OFFLINE,
                    config_json={
                        "stream_type": cam_config.stream_type,
                        "fps_cap": cam_config.fps_cap,
                        "zones": [z.model_dump() for z in cam_config.zones]
                    }
                )
                db.add(db_cam)
            else:
                existing.status = CameraStatus.ONLINE if cam_config.enabled else CameraStatus.OFFLINE
            
            if cam_config.enabled:
                try:
                    await camera_manager.add_camera(cam_config)
                    logger.info("Camera loaded at startup", camera_id=cam_config.id, name=cam_config.name)
                    
                    # Instantiate and start the CameraWorker thread
                    worker = CameraWorker(
                        config=cam_config,
                        settings=settings,
                        event_bus=event_bus,
                        camera_manager=camera_manager,
                        inference_manager=inference_manager,
                        tracking_manager=tracking_manager,
                        alert_manager=alert_manager
                    )
                    worker.start()
                    app.state.camera_workers[cam_config.id] = worker
                except Exception as ex:
                    logger.error("Failed to load camera at startup", camera_id=cam_config.id, error=str(ex))
        await db.commit()
                
    # Log system hardware info
    logger.info("System hardware capabilities:", 
                onnx_version=ort.__version__,
                available_providers=ort.get_available_providers())
                
    logger.info("Startup complete", duration_s=round(time.time() - start_time, 2))
    
    yield
    
    # Shutdown sequence
    logger.info("Shutting down Edge AI CCTV Platform...")
    
    # Stop camera workers
    for worker in getattr(app.state, "camera_workers", {}).values():
        worker.stop()
        
    # Stop cameras
    await camera_manager.stop_all()
    
    # Stop workers
    await storage_worker.stop()
    
    # Stop Event Bus
    await event_bus.stop()
    
    logger.info("Shutdown complete")
