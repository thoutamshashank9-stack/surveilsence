"""
Model Downloader — Downloads AI models for the Edge AI CCTV Analytics Platform.

Downloads:
- RT-DETRv2 R18 ONNX model from HuggingFace
- Metadata files for model registry

Usage:
    python scripts/model_downloader.py
"""

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path


# Model definitions
MODELS = {
    "rtdetrv2_r18vd": {
        "url": "https://huggingface.co/onnx-community/rtdetr_v2_r18vd-ONNX/resolve/main/onnx/model.onnx",
        "dest": "models/registry/detection/rtdetrv2_r18vd.onnx",
        "size_mb": 80,
        "description": "RT-DETRv2 R18 - Real-Time Detection Transformer (Apache-2.0)",
        "input_size": [640, 640],
        "classes": 80,
        "license": "Apache-2.0",
    },
}


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def download_file(url: str, dest_path: Path, description: str = "") -> bool:
    """Download a file with progress indication."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if dest_path.exists():
        size_mb = dest_path.stat().st_size / (1024 * 1024)
        print(f"  Already exists: {dest_path.name} ({size_mb:.1f} MB)")
        return True

    print(f"  Downloading: {description or dest_path.name}")
    print(f"     URL: {url}")

    try:
        # Create request with user agent
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "EdgeAI-CCTV-ModelDownloader/0.1"},
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 1024 * 1024  # 1MB chunks

            with open(dest_path, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        mb = downloaded / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)
                        print(
                            f"\r     Progress: {mb:.1f}/{total_mb:.1f} MB ({pct:.0f}%)",
                            end="",
                            flush=True,
                        )

            print(f"\n  Downloaded: {dest_path.name} ({downloaded / (1024*1024):.1f} MB)")
            return True

    except urllib.error.HTTPError as e:
        print(f"\n  HTTP Error {e.code}: {e.reason}")
        if dest_path.exists():
            dest_path.unlink()
        return False
    except urllib.error.URLError as e:
        print(f"\n  Network Error: {e.reason}")
        if dest_path.exists():
            dest_path.unlink()
        return False
    except Exception as e:
        print(f"\n  Error: {e}")
        if dest_path.exists():
            dest_path.unlink()
        return False


def update_metadata(root: Path) -> None:
    """Update model registry metadata."""
    metadata_path = root / "models" / "registry" / "detection" / "metadata.json"

    metadata = {
        "models": [
            {
                "name": name,
                "file": Path(info["dest"]).name,
                "input_size": info["input_size"],
                "classes": info["classes"],
                "license": info["license"],
                "description": info["description"],
            }
            for name, info in MODELS.items()
        ]
    }

    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"  Updated metadata: {metadata_path}")


def main() -> None:
    """Main entry point."""
    root = get_project_root()

    print("=" * 60)
    print("  Edge AI CCTV Analytics — Model Downloader")
    print("=" * 60)
    print()

    # Download models
    success_count = 0
    for name, info in MODELS.items():
        print(f"\nModel: {name}")
        dest = root / info["dest"]

        if download_file(info["url"], dest, info["description"]):
            success_count += 1

    # Update metadata
    print("\nUpdating model registry metadata...")
    update_metadata(root)

    # Summary
    print("\n" + "=" * 60)
    print(f"  Downloaded: {success_count}/{len(MODELS)} models")
    if success_count == len(MODELS):
        print("  All models ready!")
    else:
        print("  Some models failed to download. Check your internet connection.")
    print("=" * 60)


if __name__ == "__main__":
    main()
