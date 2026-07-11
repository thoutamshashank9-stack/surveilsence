import cv2
import numpy as np
from typing import Any, Dict
from app.ai.vlm.base import VLMBackendBase
from app.core.logging import get_logger

logger = get_logger(__name__)

# Check for ML availability
try:
    import torch
    from PIL import Image
    # Lazy import transformers inside model loader to save startup resources
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("torch/PIL not installed. Moondream2 VLM backend will run in simulated mode.")

class MoondreamVLMBackend(VLMBackendBase):
    """
    Local Moondream2 VLM inference engine supporting 4-bit quantization.
    Features Visual Embedding Caching: runs the SigLIP vision encoder once 
    and caches the vector/tensor in memory for sequential quick queries (<100ms).
    """
    def __init__(self, model_name: str = "moondream/moondream-2b-2025-04-14-4bit", device: str = "cuda"):
        self.model_name = model_name
        self.device = device if (device == "cuda" and ML_AVAILABLE and torch.cuda.is_available()) else "cpu"
        self.model = None
        self.tokenizer = None
        self.loaded = False

    def _lazy_load(self):
        if self.loaded:
            return
        
        if not ML_AVAILABLE:
            logger.info("ML packages missing. Moondream VLM running in mock mode.")
            self.loaded = True
            return

        try:
            logger.info("Lazy loading Moondream2 model", model=self.model_name, device=self.device)
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            # Load with 4-bit precision parameters
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                device_map={"": self.device} if self.device == "cuda" else None
            )
            # Compile to optimize execution speed
            if hasattr(self.model, "compile"):
                self.model = torch.compile(self.model)
                
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.loaded = True
            logger.info("Moondream2 loaded successfully")
        except Exception as e:
            logger.error("Failed to load Moondream2 model locally, falling back to mock", error=str(e))
            self.loaded = True

    def query(self, image: np.ndarray, prompt: str) -> str:
        self._lazy_load()
        if self.model is None:
            return self._query_mock(prompt)

        try:
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            # Full encode + decode pass
            return self.model.query(pil_image, prompt)["answer"].strip()
        except Exception as e:
            logger.error("Moondream query failed", error=str(e))
            return f"Moondream error: {str(e)}"

    def encode_image(self, image: np.ndarray) -> Any:
        """
        Extract and return visual embedding representation tensor.
        """
        self._lazy_load()
        if self.model is None:
            return "mock_embedding"

        try:
            import cv2
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            # Call vision encoder
            return self.model.encode_image(pil_image)
        except Exception as e:
            logger.error("Moondream encode_image failed", error=str(e))
            return None

    def query_cached(self, embedding: Any, prompt: str) -> str:
        """
        Decode query against pre-computed cached visual embedding tensor.
        """
        self._lazy_load()
        if self.model is None or embedding == "mock_embedding":
            return self._query_mock(prompt)

        try:
            # Query using cached embedding directly (bypassing SigLIP vision encoder)
            return self.model.answer_question(embedding, prompt, self.tokenizer)["answer"].strip()
        except Exception as e:
            logger.error("Moondream query_cached failed", error=str(e))
            return f"Moondream error: {str(e)}"

    def _query_mock(self, prompt: str) -> str:
        # Mock answers for local testing
        lower_prompt = prompt.lower()
        if "yes or no" in lower_prompt:
            return "Yes"
        if "category" in lower_prompt or "type" in lower_prompt:
            return "Personal Effect"
        return "Simulated Moondream2 local VLM: Object verified tucking a black item inside jacket."

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "backend": "moondream2_local",
            "model": self.model_name,
            "device": self.device,
            "quantization": "4-bit",
            "parameters": "1.86B"
        }

    def is_available(self) -> bool:
        return ML_AVAILABLE
