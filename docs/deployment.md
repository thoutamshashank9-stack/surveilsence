# Production Deployment and Architecture Documentation

This document outlines the deployment architecture, configuration steps, and operational guidelines for running the **Edge AI CCTV Security & Analytics** system in development, testing, and production environments.

---

## 1. System Architecture Overview

The platform uses a modular, event-driven microservices architecture optimized for low latency and high reliability at the edge:

```
                  +-----------------------------------+
                  |        IP Camera Stream /         |
                  |     RTSP / Mock Video Source      |
                  +-----------------+-----------------+
                                    | (OpenCV / RTSP)
                                    v
                  +-----------------+-----------------+
                  |      FastAPI Camera Workers       |
                  +--------+-----------------+--------+
                           |                 |
(Detections & Telemetry)   |                 | (Frame Analysis)
                           v                 v
           +---------------+--+     +--------+--------+
           |   Inference      |     |  Event Bus      |
           |  (ONNX/Hailo)    |     |  (Redis/Mock)   |
           +------------------+     +--------+--------+
                                             |
                                             | (Publish/Subscribe)
                                             v
                                    +--------+--------+
                                    | Storage Worker  |
                                    +--------+--------+
                                             |
                                             v
                                    +--------+--------+
                                    | sqlite/Postgres |
                                    +-----------------+
```

- **Camera Workers**: Run in independent threads, reading frames from RTSP streams, decoding with OpenCV, letterboxing, and calling the Inference Manager.
- **Inference Manager**: Selecting execution providers (CPU, CUDA, or Hailo-8 coprocessor). Runs object detection (RT-DETRv2) and object tracking (ByteTrack).
- **Event Bus**: Internal publisher/subscriber system dispatching real-time detection telemetry and zone crossing events to connected clients.
- **Storage Worker**: Persists historical track segments, analytics events, and security alert logs.

---

## 2. Docker Deployment (Recommended)

Docker Compose orchestrates the frontend, backend, and volume bindings for databases, configurations, and models registry.

### Quick Start

1. **Build and start the container stack**:
   ```bash
   docker compose up --build
   ```

2. **Access the dashboards**:
   - Web GUI Dashboard: [http://localhost:80](http://localhost:80)
   - Backend OpenAPI Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Service Definitions

- **Backend Service (`ports: 8000`)**: Mounts host directories for database storage (`./data`), model weights registry (`./models`), and configuration (`./config`).
- **Frontend Service (`ports: 80`)**: Nginx server serving compiled React assets, configured to reverse-proxy `/api/` REST requests and `/ws/` WebSocket connections back to the backend.

---

## 3. Local Bare-Metal Execution

If running outside Docker:

### Backend Setup
1. **Prepare Virtual Environment**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. **Install Dependencies**:
   ```bash
   pip install -r requirements/base.txt -r requirements/inference.txt
   ```
3. **Launch Server**:
   ```bash
   python -m uvicorn app.main:app --port 8000 --reload
   ```

### Frontend Setup
1. **Install Modules**:
   ```bash
   cd frontend
   npm install
   ```
2. **Launch Dev Server**:
   ```bash
   npm run dev
   ```

---

## 4. Multi-class Detection & VLM Verification

### Supported Classes
The detection pipeline handles COCO index mappings:
- `0`: Person (resolves to role `worker` in `worker_cabin` zone, otherwise `customer`)
- `2`: Vehicle
- `80`: Fire (triggers critical safety alerts)
- `81`: Smoke (triggers critical safety alerts)
- `82`: Weapon (triggers critical security threat alerts)

### VLM Incident Analysis
Operators can request advanced verification using the **VLM Describe** button. The system captures the camera context frame, queries the Vision-Language Model service with structured system prompts, and appends explanatory notes back to the alert log database record.
