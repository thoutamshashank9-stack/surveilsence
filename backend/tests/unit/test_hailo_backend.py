import numpy as np
from app.ai.backends.onnx_hailo import HailoInferenceBackend

def test_hailo_backend_metadata():
    backend = HailoInferenceBackend()
    assert backend.get_provider_name() == "HailoRT"
    # Should default to simulated mode on the development environment
    assert not backend.is_available()

def test_hailo_backend_inference():
    backend = HailoInferenceBackend()
    session = backend.create_session("models/registry/detection/rtdetrv2_r18.hef")
    assert session["simulated"] is True
    
    # Preprocessed dummy input image frame
    inputs = {"pixel_values": np.zeros((1, 3, 640, 640), dtype=np.float32)}
    outputs = backend.run(session, inputs)
    
    assert len(outputs) == 2
    logits, pred_boxes = outputs
    
    # Check tensor shape properties matches RT-DETRv2 models expectations
    assert logits.shape == (1, 300, 80)
    assert pred_boxes.shape == (1, 300, 4)
    
    # Verify mock detection class confidence score
    assert logits[0, 0, 0] == 0.95
    assert pred_boxes[0, 0, 0] == 0.3
