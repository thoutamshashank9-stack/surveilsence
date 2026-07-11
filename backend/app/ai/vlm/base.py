from abc import ABC, abstractmethod
from typing import Any, Dict

class VLMBackendBase(ABC):
    """
    Abstract base class for Edge-AI Vision-Language Models (VLMs).
    Supports visual embedding caching to speed up hierarchical cascade queries.
    """
    @abstractmethod
    def query(self, image: Any, prompt: str) -> str:
        """
        Executes full encoding + decoding to answer a prompt about an image.
        """
        pass

    @abstractmethod
    def encode_image(self, image: Any) -> Any:
        """
        Executes only the vision encoder, returning a cached visual embedding vector/tensor.
        """
        pass

    @abstractmethod
    def query_cached(self, embedding: Any, prompt: str) -> str:
        """
        Runs language generation head against a pre-computed cached visual embedding.
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass
