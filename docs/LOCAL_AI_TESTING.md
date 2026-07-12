# Local AI Model Execution & Data Storage Architecture Guide

This document explains the internal design of the Edge AI CCTV Platform, how your surveillance data is written and queried, and how to run real computer vision and Vision-Language Models (VLM) locally on your laptop.

---

## 1. Local AI Model Execution (Running Real Models)

By default, the platform uses lightweight, built-in mock generators if AI models or hardware execution providers are not found. To switch to the real production-grade AI pipelines on your laptop, follow these instructions:

### A. Run the Real RT-DETRv2 / YOLO Object Detectors
On startup, the system automatically attempts to load the RT-DETRv2 ResNet-18 model from `models/registry/detection/rtdetrv2_r18vd.onnx`.

To adjust detector execution settings, open `config/development.yaml` and edit the `inference` section:
```yaml
inference:
  backend: "auto"       # Options: auto | cpu | cuda (NVIDIA) | directml (Windows AMD/Intel) | openvino (Intel CPU/iGPU)
  detection:
    model: "rtdetrv2_r18"
    confidence_threshold: 0.35
    input_size: [640, 640]
    classes: [0]        # 0 = Person (standard COCO class index)
```
* **NVIDIA GPU**: Set `backend: "cuda"` to leverage TensorRT or CUDA execution.
* **AMD/Intel Integrated Graphics**: Set `backend: "directml"` to use DirectML hardware acceleration.
* **CPU Only**: Set `backend: "cpu"`. The RT-DETRv2 model runs efficiently on modern multi-core laptop CPUs.

### B. Enable Slicing Aided Hyper Inference (SAHI)
If you are monitoring a high-altitude or wide-angle stream where people appear very small in the frame, you can enable SAHI to slice incoming frames into overlapping patches:
```yaml
inference:
  detection:
    sahi:
      enabled: true
      slice_height: 640
      slice_width: 640
      overlap_ratio: 0.2
```

### C. Run the Local Visual Language Model (VLM)
The VLM is used to perform high-confidence validation of security alerts (e.g., describing the subject's clothing and verifying if a loitering event is a real hazard).

To run VLM locally via **Ollama**:
1. Download and install [Ollama](https://ollama.com/) on your laptop.
2. Run the Moondream2 model locally:
   ```bash
   ollama run moondream
   ```
3. Open `config/development.yaml` and configure the VLM section:
   ```yaml
   vlm:
     enabled: true
     backend: "ollama"   # Set to 'ollama' instead of 'simulated'
     model: "moondream"
     endpoint: "http://localhost:11434"
     timeout_seconds: 15
   ```
4. Restart the backend server. Now, when clicking the **"VLM Verify"** button on any alert card in the Alerts Feed, the server will query your local Ollama instance for a real visual explanation of the camera frame!

---

## 2. Hybrid Data Storage & Query Architecture

The platform uses a hybrid storage architecture designed to run on resource-constrained edge nodes without requiring a heavy external database server.

```
Incoming Stream ──▶ SQLite (events.db) ──▶ PyArrow Serializer ──▶ Parquet Chunks
                       (OLTP Store)          (Background Thread)      (OLAP Files)
                                                                           │
                                                                           ▼
                                                                  DuckDB OLAP Engine
                                                                 (Analytical Queries)
```

### A. The OLTP Store: SQLite (`events.db`)
* **Location**: `backend/data/events.db`
* **Purpose**: Manages all write-heavy transactional operations in real time.
* When a camera worker detects a loitering or intrusion event, the alert metadata is immediately written to the SQLite database.
* SQLite runs with **WAL (Write-Ahead Logging)** mode and async connection pools enabled, allowing concurrent reads/writes without locking the main thread.

### B. The OLAP Archive: Apache Parquet
* **Location**: `backend/data/parquet/`
* **Purpose**: Storage of historical event logs.
* A background storage worker serializes batches of SQLite event records into highly-compressed columnar **Apache Parquet** files every 5 minutes.
* This keeps the active SQLite database small and fast while preserving infinite history on disk.

### C. The Aggregation Engine: DuckDB
* **Purpose**: Performs high-speed analytics queries for the React dashboard charts (e.g. hourly entries/exits over 30 days).
* When you open the **Analytics** page, the backend uses **DuckDB** inside the Python process to query the Parquet files.
* Because DuckDB reads columnar Parquet directly, it performs aggregations across millions of rows in milliseconds, entirely bypassing the transactional SQLite database and preventing slow chart loading.
