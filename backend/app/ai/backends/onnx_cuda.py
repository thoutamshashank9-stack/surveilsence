from typing import Dict, List, Any, Optional
import onnxruntime as ort
from app.ai.backends.base import InferenceBackendBase, SessionOptionsConfig
from app.core.logging import get_logger

logger = get_logger(__name__)

class ONNXRuntimeCUDA(InferenceBackendBase):
    def create_session(self, model_path: str, options: Optional[SessionOptionsConfig] = None) -> ort.InferenceSession:
        sess_opts = ort.SessionOptions()
        
        if options:
            sess_opts.intra_op_num_threads = options.intra_op_num_threads
            sess_opts.inter_op_num_threads = options.inter_op_num_threads
            
            if options.execution_mode == "parallel":
                sess_opts.execution_mode = ort.ExecutionMode.ORT_PARALLEL
            else:
                sess_opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
                
            opt_level = getattr(ort.GraphOptimizationLevel, options.graph_optimization_level, ort.GraphOptimizationLevel.ORT_ENABLE_ALL)
            sess_opts.graph_optimization_level = opt_level

        # CUDA Execution Provider with specific configurations
        cuda_provider_options = {
            "device_id": "0",
            "arena_extend_strategy": "kSameAsRequested",
            "gpu_mem_limit": "2147483648",  # 2GB
            "cudnn_conv_algo_search": "DEFAULT",
            "do_copy_in_default_stream": "1",
        }
        
        providers = [
            ("CUDAExecutionProvider", cuda_provider_options),
            "CPUExecutionProvider"
        ]
        
        try:
            return ort.InferenceSession(model_path, sess_opts, providers=providers)
        except Exception as e:
            logger.warn("Failed to load session with CUDA provider, falling back to CPU", error=str(e))
            return ort.InferenceSession(model_path, sess_opts, providers=["CPUExecutionProvider"])

    def run(self, session: ort.InferenceSession, inputs: Dict[str, Any]) -> List[Any]:
        output_names = [o.name for o in session.get_outputs()]
        return session.run(output_names, inputs)

    def get_provider_name(self) -> str:
        return "CUDAExecutionProvider"

    def is_available(self) -> bool:
        return "CUDAExecutionProvider" in ort.get_available_providers()
