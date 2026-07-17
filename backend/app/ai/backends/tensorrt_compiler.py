import os
import sys
from pathlib import Path
from typing import Optional, Any
from app.core.logging import get_logger

logger = get_logger(__name__)

# Check if TensorRT is available
try:
    import tensorrt as trt
    TRT_AVAILABLE = True
except ImportError:
    TRT_AVAILABLE = False

class TensorRTCompiler:
    def __init__(self, precision: str = "fp16", workspace_mb: int = 1024, cache_dir: str = "models/registry/engines"):
        self.precision = precision.lower()
        self.workspace_mb = workspace_mb
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def compile(self, onnx_path: str) -> Optional[str]:
        if not TRT_AVAILABLE:
            logger.warning("TensorRT is not installed or available on this system. Cannot compile.")
            return None

        onnx_file = Path(onnx_path)
        if not onnx_file.exists():
            logger.error("ONNX model file does not exist", path=onnx_path)
            return None

        # Generate cached engine path based on model name, precision, TRT version
        try:
            trt_version = trt.__version__
            model_name = onnx_file.stem
            engine_file = self.cache_dir / f"{model_name}_{self.precision}_trt{trt_version}.engine"

            if engine_file.exists():
                logger.info("Using cached TensorRT engine", path=str(engine_file))
                return str(engine_file)

            logger.info("Compiling ONNX to TensorRT engine...", onnx_path=onnx_path, precision=self.precision)
            TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
            builder = trt.Builder(TRT_LOGGER)
            config = builder.create_builder_config()
            network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
            parser = trt.OnnxParser(network, TRT_LOGGER)

            with open(onnx_file, "rb") as model:
                if not parser.parse(model.read()):
                    for error in range(parser.num_errors):
                        logger.error("ONNX Parsing Error", error=parser.get_error(error))
                    return None

            config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, self.workspace_mb * 1024 * 1024)
            
            if self.precision == "fp16":
                if builder.platform_has_fast_fp16:
                    config.set_flag(trt.BuilderFlag.FP16)
                else:
                    logger.warning("FP16 selected but platform does not have fast FP16 support.")
            
            serialized_engine = builder.build_serialized_network(network, config)
            if serialized_engine is None:
                logger.error("Failed to build serialized engine")
                return None

            with open(engine_file, "wb") as f:
                f.write(serialized_engine)

            logger.info("TensorRT engine compiled successfully", path=str(engine_file))
            return str(engine_file)
        except Exception as e:
            logger.error("Exception occurred during TensorRT compilation", error=str(e))
            return None
