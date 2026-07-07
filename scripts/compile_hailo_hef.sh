#!/bin/bash
# ==============================================================================
# Edge AI CCTV Analytics Platform — Hailo HEF Model Compiler Pipeline Guide
# ==============================================================================
# This script lists the compilation tasks to convert the RT-DETRv2 ONNX model
# into Hailo Executable Format (HEF) using the Hailo Software Suite Docker image.

set -euo pipefail

MODEL_NAME="rtdetrv2_r18vd"
ONNX_FILE="../models/registry/detection/${MODEL_NAME}.onnx"
HAR_FILE="${MODEL_NAME}.har"
OPTIMIZED_HAR_FILE="${MODEL_NAME}_optimized.har"
HEF_OUTPUT="../models/registry/detection/rtdetrv2_r18.hef"
CALIB_DATASET="calib_images.npy" # Calibration image numpy array (subset of ~100 COCO images)

echo "=========================================================="
echo "Hailo HEF Compilation Flow — Model: ${MODEL_NAME}"
echo "=========================================================="

# 1. Start Hailo Software Suite Container
# docker run --net=host -it -v $(pwd):/workspace hailoai/software_suite:latest

# 2. Parse ONNX Model to Hailo Archive (HAR) format
echo "[1/3] Parsing ONNX model to Hailo Archive format..."
hailo parser onnx \
  --model-path "$ONNX_FILE" \
  --output-har-path "$HAR_FILE" \
  --start-node-names "pixel_values" \
  --end-node-names "logits" "pred_boxes"

# 3. Model Optimization (Quantization & Precision Adjustment)
echo "[2/3] Quantizing model weights using calibration dataset..."
# The ALLS (Allocation and Localization Script) controls compilation parameters (e.g. mapping layers to clusters)
cat <<EOF > model_config.alls
# RT-DETRv2 Optimization Configuration
# 1. Normalize input scaling parameters
normalization1 = normalization([0.0, 0.0, 0.0], [255.0, 255.0, 255.0])
# 2. Set memory optimization configurations
performance_param(fps=30)
EOF

hailo optimize \
  --har "$HAR_FILE" \
  --calib-set "$CALIB_DATASET" \
  --alls model_config.alls \
  --output-har-path "$OPTIMIZED_HAR_FILE"

# 4. Compile Optimized HAR to HEF Binary
echo "[3/3] Compiling optimized archive into Hailo-8 Target HEF..."
hailo compiler \
  --har "$OPTIMIZED_HAR_FILE" \
  --output-hef-path "$HEF_OUTPUT"

echo "=========================================================="
echo "Compilation complete! Target HEF binary written to:"
echo " -> ${HEF_OUTPUT}"
echo "=========================================================="
