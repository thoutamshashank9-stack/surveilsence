from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.lifecycle import lifespan
from app.api.v1.system import router as system_router
from app.api.v1.cameras import router as cameras_router
from app.api.v1.inference import router as inference_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.websocket import router as ws_router
from app.api.v1.webrtc import router as webrtc_router

settings = get_settings()

app = FastAPI(
    title=settings.app.name,
    version=settings.app.version,
    debug=settings.app.debug,
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in dev mode
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers under api/v1
app.include_router(system_router, prefix="/api/v1/system", tags=["system"])
app.include_router(cameras_router, prefix="/api/v1/cameras", tags=["cameras"])
app.include_router(inference_router, prefix="/api/v1/inference", tags=["inference"])
app.include_router(alerts_router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(ws_router, prefix="/api/v1/ws", tags=["websocket"])
app.include_router(webrtc_router, prefix="/api/v1", tags=["webrtc"])

@app.get("/", tags=["root"])
async def root():
    return {
        "app": settings.app.name,
        "version": settings.app.version,
        "status": "online",
        "docs_url": "/docs"
    }
