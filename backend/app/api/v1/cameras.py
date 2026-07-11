import asyncio
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Path
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_camera_manager
from app.database import get_db
from app.services.camera_manager import CameraManager
from app.models.camera import Camera
from app.models.enums import CameraStatus
from app.schemas.camera import CameraResponse, CameraCreate, CameraUpdate
from pydantic import BaseModel, Field
from app.utils.video import frame_to_jpeg
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("", response_model=List[CameraResponse], summary="List all cameras")
async def list_cameras(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camera))
    return result.scalars().all()

@router.get("/{camera_id}", response_model=CameraResponse, summary="Get camera by ID")
async def get_camera(
    camera_id: str = Path(..., description="The ID of the camera"),
    db: AsyncSession = Depends(get_db)
):
    camera = await db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera

@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED, summary="Add new camera")
async def create_camera(
    payload: CameraCreate,
    db: AsyncSession = Depends(get_db),
    camera_manager: CameraManager = Depends(get_camera_manager)
):
    # Check if ID already exists
    existing = await db.get(Camera, payload.id)
    if existing:
        raise HTTPException(status_code=400, detail="Camera ID already exists")
        
    camera = Camera(
        id=payload.id,
        name=payload.name,
        source=payload.source,
        type=payload.type,
        enabled=payload.enabled,
        status=CameraStatus.OFFLINE,
        config_json={
            "stream_type": payload.stream_type,
            "fps_cap": payload.fps_cap,
            "zones": [z.model_dump() for z in payload.zones]
        }
    )
    
    db.add(camera)
    await db.commit()
    await db.refresh(camera)
    
    # Load camera in manager
    if camera.enabled:
        await camera_manager.add_camera(payload)
        
    return camera

@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete camera")
async def delete_camera(
    camera_id: str = Path(..., description="The ID of the camera to delete"),
    db: AsyncSession = Depends(get_db),
    camera_manager: CameraManager = Depends(get_camera_manager)
):
    camera = await db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    await camera_manager.remove_camera(camera_id)
    await db.delete(camera)
    await db.commit()

@router.get("/{camera_id}/stream", summary="Stream camera live MJPEG feed")
async def stream_camera(
    camera_id: str = Path(..., description="The ID of the camera to stream"),
    camera_manager: CameraManager = Depends(get_camera_manager)
):
    """Multipart boundary stream transmitting BGR frames encoded as JPEGs."""
    if camera_manager.get_status(camera_id) == CameraStatus.OFFLINE:
        # Try starting mock stream
        pass
        
    async def frame_generator():
        while True:
            ret, frame = camera_manager.get_frame(camera_id)
            if ret and frame is not None:
                try:
                    jpeg_bytes = frame_to_jpeg(frame, quality=70)
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n"
                    )
                except Exception as ex:
                    logger.error("Error generating stream frame", camera_id=camera_id, error=str(ex))
            # Limit loop rate
            await asyncio.sleep(0.04)  # ~25 FPS max
            
    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

class CalibrationRequest(BaseModel):
    pixel_points: List[List[float]] = Field(..., description="4 points in pixel coordinates [[x,y], ...]")
    world_points: List[List[float]] = Field(..., description="4 points in ground plane meters [[X,Y], ...]")

@router.post("/{camera_id}/calibrate", summary="Calibrate camera homography projection matrix")
async def calibrate_camera(
    camera_id: str = Path(..., description="The ID of the camera to calibrate"),
    payload: CalibrationRequest = None,
    db: AsyncSession = Depends(get_db)
):
    camera = await db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    if len(payload.pixel_points) != 4 or len(payload.world_points) != 4:
        raise HTTPException(status_code=400, detail="Calibration requires exactly 4 point matches")

    from app.ai.postprocessing.homography import HomographyCalibrator
    calibrator = HomographyCalibrator()
    success = calibrator.calibrate(payload.pixel_points, payload.world_points)
    if not success:
        raise HTTPException(status_code=400, detail="Homography calibration failed. Points might be collinear or invalid.")

    # Update camera's homography config in database
    cfg = dict(camera.config_json or {})
    cfg["homography"] = {
        "enabled": True,
        "pixel_points": payload.pixel_points,
        "world_points": payload.world_points,
        "matrix_H": calibrator.H.tolist()
    }
    camera.config_json = cfg
    await db.commit()
    
    logger.info("Camera homography matrix calibrated and saved", camera_id=camera_id)
    return {"status": "success", "matrix_H": calibrator.H.tolist()}

