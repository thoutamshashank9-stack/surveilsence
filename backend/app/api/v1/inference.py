from fastapi import APIRouter, Depends
from app.api.deps import get_inference_manager
from app.services.inference_manager import InferenceManager

router = APIRouter()

@router.get("/status", summary="Get active inference details")
async def get_status(inference_manager: InferenceManager = Depends(get_inference_manager)):
    """Return configured model dimensions, confidence levels, and active execution backend."""
    return inference_manager.get_status()
