import random
import numpy as np
from typing import Any, Dict
from app.config import VLMConfig
from app.ai.vlm.base import VLMBackendBase
from app.ai.vlm.ollama_backend import OllamaVLMBackend
from app.ai.vlm.moondream_backend import MoondreamVLMBackend
from app.ai.vlm.paligemma_backend import PaliGemmaVLMBackend

class SimulatedVLMBackend(VLMBackendBase):
    """
    Simulated VLM backend generating plausible CCTV scene descriptions.
    """
    def __init__(self, model_name: str = "simulated"):
        self.model_name = model_name

    def query(self, image: np.ndarray, prompt: str) -> str:
        # Move existing simulated text generator from vlm_service.py
        lower_prompt = prompt.lower()
        
        actions = ["walking slowly", "carrying a cardboard box", "stopping near the door", "inspecting the register area", "bending down to adjust shoes"]
        clothing_colors = ["red", "dark blue", "black", "grey hoodie", "green jacket", "white t-shirt"]
        clothing_types = ["jeans", "shorts", "sweatpants", "sneakers"]
        items = ["backpack", "shoulder bag", "handbag", "umbrella", "mobile phone"]
        
        c_color = random.choice(clothing_colors)
        c_type = random.choice(clothing_types)
        item = random.choice(items)
        action = random.choice(actions)
        
        desc = f"Subject wearing a {c_color} with {c_type}, carrying a {item}, seen {action}."
        
        if "yes or no" in lower_prompt:
            return "Yes"
        if "category" in lower_prompt or "type" in lower_prompt:
            return "Personal Effect"
            
        return f"SIMULATED VERIFICATION: {desc}"

    def encode_image(self, image: np.ndarray) -> str:
        return "mock_embedding"

    def query_cached(self, embedding: str, prompt: str) -> str:
        return self.query(None, prompt)

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "backend": "simulated",
            "model": self.model_name
        }

    def is_available(self) -> bool:
        return True

def create_vlm_backend(config: VLMConfig) -> VLMBackendBase:
    """
    VLM Factory to select and instantiate VLM backends.
    """
    backend_type = getattr(config, "backend", "ollama").lower()
    
    if backend_type == "moondream2":
        return MoondreamVLMBackend(model_name=config.model)
    elif backend_type == "paligemma":
        return PaliGemmaVLMBackend(model_name=config.model)
    elif backend_type == "ollama" and config.enabled:
        return OllamaVLMBackend(
            endpoint=config.endpoint,
            model_name=config.model,
            timeout_seconds=config.timeout_seconds
        )
    
    return SimulatedVLMBackend()
