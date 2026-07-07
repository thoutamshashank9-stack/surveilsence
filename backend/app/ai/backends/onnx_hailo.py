import os
import numpy as np
from typing import Dict, List, Any, Optional
from app.ai.backends.base import InferenceBackendBase, SessionOptionsConfig
from app.core.logging import get_logger

logger = get_logger(__name__)

class HailoInferenceBackend(InferenceBackendBase):
    def __init__(self):
        self._available = False
        try:
            # Try importing native HailoRT library
            import hailort
            self._available = True
            logger.info("HailoRT native Python bindings loaded successfully.")
        except ImportError:
            logger.info("HailoRT libraries not found. Operating Hailo Backend in simulated/mock model mode.")

    def is_available(self) -> bool:
        return self._available

    def get_provider_name(self) -> str:
        return "HailoRT"

    def create_session(self, model_path: str, options: Optional[SessionOptionsConfig] = None) -> Any:
        """
        Load compiled Hailo Executable Format (HEF) file and configure target PCIE devices.
        Returns a session runner object (real or simulated).
        """
        logger.info("Configuring Hailo-8 hardware target session", hef_path=model_path)
        
        if not self._available:
            logger.warning("HailoRT not available. Creating simulated Hailo session runner.")
            # Return dummy runner properties
            return {
                "simulated": True,
                "model_path": model_path,
                "input_shape": (1, 3, 640, 640),
                "output_shapes": {
                    "logits": (1, 300, 80),
                    "pred_boxes": (1, 300, 4)
                }
            }

        # Native HailoRT device allocation flow
        from hailort import Device, HEF
        
        try:
            device = Device.create_pcie_device()
            hef = HEF(model_path)
            
            # Configure network groups
            network_groups = device.configure(hef)
            network_group = network_groups[0]
            
            # Retrieve virtual stream details
            input_vstream_infos = hef.get_input_vstream_infos()
            output_vstream_infos = hef.get_output_vstream_infos()
            
            logger.info(
                "Hailo hardware session configured successfully",
                inputs=len(input_vstream_infos),
                outputs=len(output_vstream_infos)
            )
            
            return {
                "simulated": False,
                "device": device,
                "hef": hef,
                "network_group": network_group,
                "input_infos": input_vstream_infos,
                "output_infos": output_vstream_infos
            }
        except Exception as e:
            logger.error("Failed to initialize physical Hailo hardware session", error=str(e))
            raise RuntimeError(f"Hailo hardware setup error: {e}")

    def run(self, session: Any, inputs: Dict[str, Any]) -> List[Any]:
        """
        Feed preprocessed input tensors through the Hailo VStreams.
        Returns the output logits and pred_boxes arrays.
        """
        # If simulated runner, generate realistic dummy detections
        if session.get("simulated", True):
            # Generate logits [1, 300, 80] and bounding box coordinates [1, 300, 4]
            # Person class id is 0 in coco format
            logits = np.zeros((1, 300, 80), dtype=np.float32)
            pred_boxes = np.zeros((1, 300, 4), dtype=np.float32)
            
            # Simulate a few people in the frame
            logits[0, 0, 0] = 0.95  # Person 1 high confidence
            pred_boxes[0, 0] = [0.3, 0.4, 0.1, 0.2]  # cx, cy, w, h
            
            logits[0, 1, 0] = 0.85  # Person 2
            pred_boxes[0, 1] = [0.6, 0.5, 0.15, 0.25]
            
            return [logits, pred_boxes]

        # Native HailoRT virtual stream inference transmission
        from hailort import InferVStreams
        
        network_group = session["network_group"]
        input_data = inputs[next(iter(inputs))] # Get first input value (pixel values)
        
        # Ensure correct data type (usually uint8/float32 depending on HEF format)
        if input_data.dtype != np.float32:
            input_data = input_data.astype(np.float32)

        # Allocate virtual input/output stream buffers
        input_dict = {session["input_infos"][0].name: input_data}
        output_dict = {info.name: np.empty(info.shape, dtype=np.float32) for info in session["output_infos"]}
        
        # Perform inference context session call
        with InferVStreams(network_group, session["input_infos"], session["output_infos"]) as infer_pipeline:
            infer_pipeline.infer(input_dict, output_dict)
            
        # Return ordered outputs (logits followed by pred_boxes)
        # Hailo outputs are mapped back to align with RT-DETRv2 models expectations
        logits_key = next(k for k in output_dict.keys() if "logits" in k.lower() or "pred" not in k.lower())
        boxes_key = next(k for k in output_dict.keys() if "box" in k.lower() or "pred" in k.lower())
        
        return [output_dict[logits_key], output_dict[boxes_key]]
