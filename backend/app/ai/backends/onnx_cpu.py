from typing import Dict, List, Any, Optional
import onnxruntime as ort
from app.ai.backends.base import InferenceBackendBase, SessionOptionsConfig

class ONNXRuntimeCPU(InferenceBackendBase):
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

        providers = ["CPUExecutionProvider"]
        return ort.InferenceSession(model_path, sess_opts, providers=providers)

    def run(self, session: ort.InferenceSession, inputs: Dict[str, Any]) -> List[Any]:
        output_names = [o.name for o in session.get_outputs()]
        return session.run(output_names, inputs)

    def get_provider_name(self) -> str:
        return "CPUExecutionProvider"

    def is_available(self) -> bool:
        return "CPUExecutionProvider" in ort.get_available_providers()
