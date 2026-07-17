import os
import json
import hashlib
import urllib.request
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Only commercially safe licenses allowed in production
ALLOWED_LICENSES = {"Apache-2.0", "MIT", "BSD-2-Clause", "BSD-3-Clause"}
BLOCKED_LICENSES = {"AGPL-3.0", "GPL-3.0", "CC-BY-NC", "proprietary-ultralytics"}

class LicenseError(RuntimeError):
    pass

class ModelMissingError(RuntimeError):
    pass

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def ensure_model(task: str, model_id: str, registry_root: Path, allow_download: bool = True) -> Path:
    meta_path = registry_root / task / "metadata.json"
    if not meta_path.exists():
        # Fallback to check if a nested directory style exists
        nested_meta_path = registry_root / task / model_id / "metadata.json"
        if nested_meta_path.exists():
            meta_path = nested_meta_path
        else:
            # Fallback to general metadata in registry root (e.g. for detection)
            general_meta_path = registry_root / "metadata.json"
            if general_meta_path.exists() and task == "detection":
                meta_path = general_meta_path
            else:
                raise ModelMissingError(f"Missing metadata for task/model: {task}/{model_id} at {meta_path}")

    try:
        with open(meta_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        raise ModelMissingError(f"Failed to read metadata for {task}/{model_id}: {str(e)}")

    # Find the specific model inside metadata
    models_list = data.get("models", [])
    meta = None
    for m in models_list:
        m_name = m.get("name", "")
        m_id = m.get("model_id", "")
        if m_name == model_id or m_id == model_id or model_id in m_name or m_name in model_id:
            meta = m
            break

    if not meta:
        # Fallback: if data is a direct dict representing the model itself
        if isinstance(data, dict):
            m_name = data.get("name", "")
            m_id = data.get("model_id", "")
            if m_name == model_id or m_id == model_id or model_id in m_name or m_name in model_id:
                meta = data
        else:
            raise ModelMissingError(f"Model ID '{model_id}' not found in task '{task}' metadata")

    lic = meta.get("license", "UNKNOWN")
    if lic in BLOCKED_LICENSES or lic not in ALLOWED_LICENSES:
        raise LicenseError(
            f"Model {task}/{model_id} license '{lic}' is not allowed for commercial use. "
            f"Allowed: {sorted(ALLOWED_LICENSES)}"
        )

    rel_file = meta.get("file") or meta.get("onnx_file")
    if not rel_file:
        raise ModelMissingError(f"No file defined in metadata for {task}/{model_id}")

    path = meta_path.parent / rel_file
    expected = meta.get("sha256")
    url = meta.get("download_url")

    if not path.exists():
        if not allow_download or not url:
            raise ModelMissingError(
                f"Model file missing: {path}. Place ONNX there or set download_url in metadata.json"
            )
        logger.info("Downloading model", task=task, model_id=model_id, url=url)
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, path)

    if expected:
        got = _sha256(path)
        if got != expected:
            path.unlink(missing_ok=True)
            raise ModelMissingError(f"Checksum mismatch for {path}: {got} != {expected}")

    return path

class ModelRegistry:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.registry_path = Path(settings.inference.detection.model_path).parent

    def get_model_path(self, model_name: str, task: str = "detection") -> Optional[str]:
        try:
            # We don't download by default in get_model_path to keep it fast
            path = ensure_model(task, model_name, self.registry_path, allow_download=False)
            return str(path)
        except Exception as e:
            logger.error("Error retrieving model path", model=model_name, error=str(e))
            return None

    def list_models(self, task: str = "detection") -> List[Dict[str, Any]]:
        meta_file = self.registry_path / task / "metadata.json"
        if not meta_file.exists():
            # Check detection root fallback
            if task == "detection":
                meta_file = self.registry_path / "metadata.json"
            else:
                return []
            
        if not meta_file.exists():
            return []
            
        try:
            with open(meta_file, "r") as f:
                data = json.load(f)
            models = data.get("models", [])
            for m in models:
                file_path = meta_file.parent / m.get("file", "")
                m["downloaded"] = file_path.exists()
                m["size_mb"] = round(file_path.stat().st_size / (1024 * 1024), 1) if file_path.exists() else 0.0
            return models
        except Exception as e:
            logger.error("Error listing registry models", error=str(e))
            return []
            
    def is_model_available(self, model_name: str, task: str = "detection") -> bool:
        return self.get_model_path(model_name, task) is not None
