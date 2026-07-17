from typing import Dict, List, Any, Optional
import onnxruntime as ort
from app.ai.backends.base import InferenceBackendBase, SessionOptionsConfig
from app.core.logging import get_logger

logger = get_logger(__name__)

class TensorRTBackend(InferenceBackendBase):
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

        # TensorRT Execution Provider options
        trt_options = {
            "device_id": "0",
            "trt_max_workspace_size": "1073741824",  # 1GB
            "trt_fp16_enable": "1",                  # Enable FP16
            "trt_engine_cache_enable": "1",          # Cache TRT engine to disk
            "trt_engine_cache_path": "models/registry/engines",
            "trt_dump_subgraphs": "0"
        }
        
        providers = [
            ("TensorrtExecutionProvider", trt_options),
            "CUDAExecutionProvider",
            "CPUExecutionProvider"
        ]
        
        try:
            import os
            os.makedirs("models/registry/engines", exist_ok=True)
            logger.info("Initializing ONNX Runtime Session with TensorRT Provider", path=model_path)
            return ort.InferenceSession(model_path, sess_opts, providers=providers)
        except Exception as e:
            logger.warning("Failed to initialize TensorRT session, falling back to CUDA/CPU", error=str(e))
            return ort.InferenceSession(model_path, sess_opts, providers=["CUDAExecutionProvider", "CPUExecutionProvider"])

    def run(self, session: ort.InferenceSession, inputs: Dict[str, Any]) -> List[Any]:
        output_names = [o.name for o in session.get_outputs()]
        return session.run(output_names, inputs)

    def get_provider_name(self) -> str:
        return "TensorrtExecutionProvider"

    def is_available(self) -> bool:
        return "TensorrtExecutionProvider" in ort.get_available_providers()
