import httpx
import base64
import cv2
import numpy as np
from typing import Any, Dict
from app.ai.vlm.base import VLMBackendBase
from app.core.logging import get_logger

logger = get_logger(__name__)

class OllamaVLMBackend(VLMBackendBase):
    """
    Ollama-based VLM backend querying localized endpoints (e.g. LLaVA, BakLLaVA).
    Does not support visual embedding caching since model execution is handled 
    remotely via REST API.
    """
    def __init__(self, endpoint: str, model_name: str, timeout_seconds: int = 10):
        self.endpoint = f"{endpoint}/api/generate"
        self.model_name = model_name
        self.timeout = timeout_seconds
        logger.info("Ollama VLM Backend initialized", endpoint=self.endpoint, model=self.model_name)

    def _frame_to_base64(self, image: np.ndarray) -> str:
        # Encode image to JPEG then to base64
        ret, buffer = cv2.imencode('.jpg', image)
        if not ret:
            raise ValueError("Failed to encode image to JPEG")
        return base64.b64encode(buffer).decode('utf-8')

    def query(self, image: np.ndarray, prompt: str) -> str:
        # Sync wrapper since VLMBackendBase interface is synchronous
        # (executed inside thread executor if called from async)
        try:
            b64_image = self._frame_to_base64(image)
            resp = httpx.post(
                self.endpoint,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "images": [b64_image],
                    "stream": False
                },
                timeout=self.timeout
            )
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
            else:
                logger.error("Ollama query failed with bad status code", status_code=resp.status_code)
                return "Error: Ollama query failed."
        except Exception as e:
            logger.error("Ollama query failed with exception", error=str(e))
            return f"Ollama connection error: {str(e)}"

    def encode_image(self, image: np.ndarray) -> str:
        # Return base64 string directly as cached representation
        return self._frame_to_base64(image)

    def query_cached(self, embedding: str, prompt: str) -> str:
        # Send raw query using cached base64 image representation
        try:
            resp = httpx.post(
                self.endpoint,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "images": [embedding],
                    "stream": False
                },
                timeout=self.timeout
            )
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
            return "Error: Ollama cached query failed."
        except Exception as e:
            logger.error("Ollama cached query failed", error=str(e))
            return f"Ollama connection error: {str(e)}"

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "backend": "ollama",
            "model": self.model_name,
            "endpoint": self.endpoint
        }

    def is_available(self) -> bool:
        try:
            # Simple ping
            base_url = self.endpoint.replace("/api/generate", "")
            resp = httpx.get(base_url, timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False
