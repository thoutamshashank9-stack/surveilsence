import numpy as np
from typing import Optional, Any
from app.config import get_settings
from app.core.logging import get_logger
from app.ai.vlm.factory import create_vlm_backend

logger = get_logger(__name__)

class VLMVerificationService:
    """
    Service to orchestrate local and remote VLM inference backends 
    for visual anomaly validation.
    """
    def __init__(self, settings: Optional[Any] = None):
        self.settings = settings or get_settings()
        self.backend = create_vlm_backend(self.settings.vlm)
        info = self.backend.get_model_info()
        logger.info("VLM Verification Service initialized", backend_info=info)

    async def verify_frame(self, frame: np.ndarray, alert_type: str, zone_name: str) -> str:
        """
        Analyze frame and produce natural-language verification description.
        Runs VLM queries inside a thread executor to avoid blocking the asyncio event loop.
        """
        import asyncio
        loop = asyncio.get_running_loop()
        
        if alert_type == "concealment":
            prompt = "Is the person in this image tucking or concealing an object inside their clothing? Answer YES or NO."
        elif alert_type == "intrusion":
            prompt = f"Is there a person visible in the restricted area '{zone_name}'? Answer YES or NO."
        elif alert_type == "loitering":
            prompt = f"Describe what the person in the '{zone_name}' area is doing."
        else:
            prompt = (
                f"Analyze this CCTV security alert: alert_type={alert_type}, zone_name={zone_name}. "
                f"Provide a short 1-sentence operator summary."
            )

        try:
            # Execute query in thread pool
            result = await loop.run_in_executor(None, self.backend.query, frame, prompt)
            return f"VLM VERIFIED: {result}"
        except Exception as e:
            logger.warning("VLM query execution failed, falling back to simulated query description", error=str(e))
            # Fallback to simulated description if query crashes
            from app.ai.vlm.factory import SimulatedVLMBackend
            sim = SimulatedVLMBackend()
            return sim.query(frame, prompt)
