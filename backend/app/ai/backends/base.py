from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import onnxruntime as ort

@dataclass
class SessionOptionsConfig:
    intra_op_num_threads: int = 4
    inter_op_num_threads: int = 2
    execution_mode: str = "sequential"  # sequential, parallel
    graph_optimization_level: str = "ORT_ENABLE_ALL"
    extra_options: Dict[str, str] = field(default_factory=dict)

class InferenceBackendBase(ABC):
    @abstractmethod
    def create_session(self, model_path: str, options: Optional[SessionOptionsConfig] = None) -> ort.InferenceSession:
        pass

    @abstractmethod
    def run(self, session: ort.InferenceSession, inputs: Dict[str, Any]) -> List[Any]:
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass
