import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, List, Any
from pathlib import Path

from app.config import get_settings, Settings
from app.services.model_registry import ModelRegistry, ensure_model, DOWNLOAD_PROGRESS

router = APIRouter()

def get_registry(settings: Settings = Depends(get_settings)) -> ModelRegistry:
    return ModelRegistry(settings)

@router.get("/")
def list_all_models(registry: ModelRegistry = Depends(get_registry)) -> Dict[str, List[Dict[str, Any]]]:
    """
    List all configured models across tasks and their download/license status.
    """
    tasks = ["detection", "pose", "tracking"]
    results = {}
    for task in tasks:
        results[task] = registry.list_models(task)
    return results

@router.get("/progress")
def get_download_progress() -> Dict[str, Any]:
    """
    Get active download progress status.
    """
    return DOWNLOAD_PROGRESS

def _download_task(task: str, name: str, registry_root: Path):
    try:
        ensure_model(task, name, registry_root, allow_download=True)
    except Exception as e:
        # State update is handled inside download_file_with_resume
        pass

@router.post("/{task}/{name}/download")
def download_model(
    task: str, 
    name: str, 
    background_tasks: BackgroundTasks,
    registry: ModelRegistry = Depends(get_registry)
) -> Dict[str, str]:
    """
    Trigger download of a specific model in the background.
    """
    models = registry.list_models(task)
    model_exists = any(m.get("name") == name for m in models)
    if not model_exists:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found in task '{task}' metadata")

    # If already downloading, return status
    if name in DOWNLOAD_PROGRESS and DOWNLOAD_PROGRESS[name]["status"] == "downloading":
        return {"status": "already_downloading", "message": f"Model '{name}' download is in progress."}

    background_tasks.add_task(_download_task, task, name, registry.registry_path)
    return {"status": "started", "message": f"Started download of '{name}' for task '{task}' in the background."}

@router.get("/status")
def get_models_readiness_status(registry: ModelRegistry = Depends(get_registry)) -> Dict[str, Any]:
    """
    Get general readiness status of all required models based on active configurations.
    """
    settings = get_settings()
    registry_root = registry.registry_path
    
    required = [
        ("detection", settings.inference.detection.model)
    ]
    if settings.behavioral.concealment.enabled and settings.behavioral.concealment.pose.enabled:
        required.append(("pose", settings.behavioral.concealment.pose.model_id))
    if settings.inference.tracking.cross_camera.enabled:
        required.append(("tracking", settings.inference.tracking.cross_camera.reid.model_path))

    readiness = {}
    all_ready = True
    for task, model_id in required:
        if not model_id:
            continue
        available = registry.is_model_available(model_id, task)
        readiness[f"{task}:{model_id}"] = "READY" if available else "MISSING"
        if not available:
            all_ready = False

    return {
        "all_ready": all_ready,
        "details": readiness
    }
