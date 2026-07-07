import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class ModelRegistry:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.registry_path = Path(settings.inference.detection.model_path).parent

    def get_model_path(self, model_name: str) -> Optional[str]:
        metadata_file = self.registry_path / "metadata.json"
        if not metadata_file.exists():
            return None
            
        try:
            with open(metadata_file, "r") as f:
                data = json.load(f)
            for m in data.get("models", []):
                if m.get("name") == model_name:
                    full_path = self.registry_path / m.get("file")
                    if full_path.exists():
                        return str(full_path)
        except Exception as e:
            logger.error("Error reading model registry metadata", error=str(e))
            
        return None

    def list_models(self) -> List[Dict[str, Any]]:
        metadata_file = self.registry_path / "metadata.json"
        if not metadata_file.exists():
            return []
            
        try:
            with open(metadata_file, "r") as f:
                data = json.load(f)
            models = data.get("models", [])
            for m in models:
                # Add download/local status
                file_path = self.registry_path / m.get("file", "")
                m["downloaded"] = file_path.exists()
                m["size_mb"] = round(file_path.stat().st_size / (1024 * 1024), 1) if file_path.exists() else 0.0
            return models
        except Exception as e:
            logger.error("Error listing registry models", error=str(e))
            return []
            
    def is_model_available(self, model_name: str) -> bool:
        return self.get_model_path(model_name) is not None
