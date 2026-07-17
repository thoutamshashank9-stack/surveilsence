#!/usr/bin/env python
import os
import sys
import argparse
from pathlib import Path

# Add backend directory to sys.path
scripts_dir = Path(__file__).resolve().parent
backend_dir = scripts_dir.parent
sys.path.append(str(backend_dir))

from app.config import get_settings
from app.ai.backends.tensorrt_compiler import TensorRTCompiler, TRT_AVAILABLE

def main():
    parser = argparse.ArgumentParser(description="TensorRT Engine Compilation Utility")
    parser.add_argument("--model", type=str, required=True, help="Path to input ONNX model file")
    parser.add_argument("--precision", type=str, default="fp16", choices=["fp32", "fp16", "int8"], help="Precision mode")
    parser.add_argument("--workspace", type=int, default=1024, help="Max workspace limit in MB")
    parser.add_argument("--cache-dir", type=str, default="../models/registry/engines", help="Engine cache output directory")
    
    args = parser.parse_args()
    
    print("=========================================")
    # Use a human-readable model name string
    print("Edge AI - TensorRT Optimization Compiler")
    print("=========================================")
    
    if not TRT_AVAILABLE:
        print("ERROR: TensorRT is not available/installed on this system.")
        print("Please run this command on an NVIDIA Linux environment with TensorRT installed.")
        sys.exit(1)
        
    compiler = TensorRTCompiler(
        precision=args.precision,
        workspace_mb=args.workspace,
        cache_dir=args.cache_dir
    )
    
    engine_path = compiler.compile(args.model)
    if engine_path:
        print(f"\nSUCCESS: TensorRT engine generated at: {engine_path}")
        sys.exit(0)
    else:
        print("\nERROR: Failed to compile TensorRT engine.")
        sys.exit(1)

if __name__ == "__main__":
    main()
