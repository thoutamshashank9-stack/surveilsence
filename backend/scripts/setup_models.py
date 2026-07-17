#!/usr/bin/env python
import os
import sys
from pathlib import Path

# Add backend directory to sys.path so we can import app modules
scripts_dir = Path(__file__).resolve().parent
backend_dir = scripts_dir.parent
sys.path.append(str(backend_dir))

from app.config import get_settings
from app.services.model_registry import ModelRegistry, ensure_model, ALLOWED_LICENSES

def main():
    print("==================================================")
    print("Edge AI Platform - Model Registry Setup Downloader")
    print("==================================================")
    
    settings = get_settings()
    registry = ModelRegistry(settings)
    registry_root = registry.registry_path
    
    tasks = ["detection", "pose", "tracking"]
    
    print(f"Registry Root: {registry_root.resolve()}")
    print("Scanning task metadata registries...\n")
    
    all_success = True
    for task in tasks:
        print(f"Task: {task}")
        models = registry.list_models(task)
        if not models:
            print(f"  No models found in {task} metadata.json")
            continue
            
        for model in models:
            name = model.get("name")
            downloaded = model.get("downloaded", False)
            license_type = model.get("license", "UNKNOWN")
            url = model.get("download_url")
            
            status_str = "[OK] Installed" if downloaded else "[ ] Missing"
            print(f"  - Model: {name} ({license_type})")
            print(f"    Status: {status_str}")
            
            if license_type not in ALLOWED_LICENSES:
                print(f"    WARNING: License '{license_type}' is blocked or not approved for commercial use!")
                continue
                
            if not downloaded:
                if not url:
                    print("    ERROR: No download URL configured in metadata.json!")
                    all_success = False
                    continue
                print(f"    Action: Downloading from {url}...")
                try:
                    ensure_model(task, name, registry_root, allow_download=True)
                    print("    Result: Success!")
                except Exception as e:
                    print(f"    Result: Failed to download model! Error: {e}")
                    all_success = False
            else:
                print("    Action: None (already installed)")
                
    print("\n==================================================")
    if all_success:
        print("Setup Completed Successfully.")
        sys.exit(0)
    else:
        print("Setup Completed with Errors.")
        sys.exit(1)

if __name__ == "__main__":
    main()
