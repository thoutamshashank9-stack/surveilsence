from typing import Dict, List, Any, Optional
import onnxruntime as ort
from app.ai.backends.base import InferenceBackendBase, SessionOptionsConfig
from app.core.logging import get_logger

logger = get_logger(__name__)

class ONNXRuntimeDirectML(InferenceBackendBase):
    """
    DirectML execution provider for AMD Radeon iGPU / discrete GPU inference.

    CRITICAL CONSTRAINTS (documented AMD APU Surveillance Blueprint):
    1. Execution mode MUST be ORT_SEQUENTIAL — parallel mode causes E_INVALIDARG (0x80070057).
    2. Memory pattern optimization MUST be disabled — incompatible with DirectX 12 compute queues.
    3. Multi-threaded Run() on the SAME session is PROHIBITED.
       - Use session-per-camera (one InferenceSession per camera thread), or
       - Use DynamicFrameBatcher to serialize inference through a single session.
    """

    def create_session(self, model_path: str, options: Optional[SessionOptionsConfig] = None) -> ort.InferenceSession:
        sess_opts = ort.SessionOptions()

        # MANDATORY: DirectML does not support parallel execution.
        # Attempting parallel mode triggers RuntimeException or E_INVALIDARG (0x80070057).
        sess_opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

        # MANDATORY: DirectML does not support memory pattern optimizations.
        sess_opts.enable_mem_pattern = False

        # Apply thread configuration from options if provided
        if options:
            sess_opts.intra_op_num_threads = options.intra_op_num_threads
            sess_opts.inter_op_num_threads = options.inter_op_num_threads

            opt_level = getattr(
                ort.GraphOptimizationLevel,
                options.graph_optimization_level,
                ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            )
            sess_opts.graph_optimization_level = opt_level

        providers = [
            ("DmlExecutionProvider", {"device_id": 0}),
            "CPUExecutionProvider"
        ]

        try:
            session = ort.InferenceSession(model_path, sess_opts, providers=providers)
            active = session.get_providers()
            logger.info(
                "DirectML session created successfully",
                providers=active,
                model=model_path
            )
            return session
        except Exception as e:
            logger.warning(
                "Failed to create DirectML session, falling back to CPU",
                error=str(e)
            )
            return ort.InferenceSession(
                model_path, sess_opts, providers=["CPUExecutionProvider"]
            )

    def run(self, session: ort.InferenceSession, inputs: Dict[str, Any]) -> List[Any]:
        output_names = [o.name for o in session.get_outputs()]
        return session.run(output_names, inputs)

    def get_provider_name(self) -> str:
        return "DmlExecutionProvider"

    def is_available(self) -> bool:
        return "DmlExecutionProvider" in ort.get_available_providers()

