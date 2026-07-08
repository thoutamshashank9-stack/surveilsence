# Edge AI CCTV Analytics Platform

**Commercial-Grade • Hardware-Agnostic • Multi-Camera • Cloud-Edge Hybrid**

A production-ready Edge AI CCTV Analytics Platform that converts standard cameras into intelligent security and business analytics units. Deployed from a single codebase across development laptops, Intel N100 mini PCs, NVIDIA Jetson, and RTX workstations.

## Architecture

```
Camera Sources ──▶ Frame Decoder ──▶ RT-DETRv2 (ONNX) ──▶ ByteTrack ──▶ Zone Rules ──▶ Events/Alerts
      │                                                                                      │
      └──────── MJPEG/WebSocket ◀──── React Dashboard ◀──── FastAPI ◀──── SQLite/PostgreSQL ─┘
```

## Technology Stack

| Layer | Technology | License |
|-------|-----------|---------|
| Detection | RT-DETRv2 R18 (ONNX INT8) | Apache-2.0 |
| Tracking | ByteTrack | MIT |
| VLM | SmolVLM-256M (GGUF) | Apache-2.0 |
| Inference | ONNX Runtime (CPU/CUDA/DirectML/OpenVINO) | MIT |
| Backend | FastAPI + SQLAlchemy | MIT |
| Frontend | React + TypeScript + Vite | MIT |
| Database | SQLite (dev) / PostgreSQL + TimescaleDB (prod) | Public Domain / PostgreSQL |

**100% commercial-safe** — zero AGPL/GPL runtime dependencies.

## Hardware Compatibility

| Hardware | Max Cameras (4MP@15FPS) | Inference Backend |
|----------|------------------------|-------------------|
| Dev Laptop (AMD/Intel + iGPU) | 2–4 | ONNX CPU / DirectML |
| Intel N100 Mini PC | 2–4 | OpenVINO / ONNX CPU |
| Jetson Orin Nano 8GB | 8–12 | TensorRT / ONNX CUDA |
| RTX 4060 (8GB) | 24–32 | TensorRT / ONNX CUDA |
| RTX 4080 (16GB) | 64+ | TensorRT / ONNX CUDA |

## Quick Start

The fastest way to deploy the entire platform (frontend, backend, database, configuration, and VLM/camera mocks) is using **Docker Compose**:

```bash
docker compose up --build
```
Once started:
- Access the React GUI Dashboard at: [http://localhost:80](http://localhost:80)
- Access the FastAPI Swagger Documentation at: [http://localhost:8000/docs](http://localhost:8000/docs)

For more detailed setup options, refer to the [Deployment Guide](docs/deployment.md).

### Local Bare-Metal Installation

### Prerequisites
- Python 3.11 or 3.12
- Node.js 18+
- Git

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements/base.txt -r requirements/inference.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Download Models
```bash
python scripts/model_downloader.py
```

## Project Structure

```
├── backend/          # FastAPI + AI inference pipeline
│   ├── app/
│   │   ├── ai/       # Detection, tracking, VLM, inference backends
│   │   ├── api/      # REST + WebSocket endpoints
│   │   ├── core/     # Logging, security, events, lifecycle
│   │   ├── models/   # SQLAlchemy ORM models
│   │   ├── schemas/  # Pydantic request/response schemas
│   │   ├── services/ # Business logic (camera, alerts, analytics)
│   │   └── workers/  # Background processing tasks
│   └── tests/
├── frontend/         # React + Vite + TypeScript dashboard
├── config/           # YAML profiles (dev, prod, inference, cameras)
├── models/           # AI model registry (ONNX, GGUF)
├── scripts/          # Dev tools, model download, benchmarks
├── docker/           # Container definitions
└── docs/             # Architecture, API, deployment docs
```

## Core Features

- **Real-time object detection** — Person, vehicle, fire, smoke, weapon, PPE
- **Multi-object tracking** — Stable IDs across frames with occlusion handling
- **Zone analytics** — Intrusion detection, line crossing, dwell time, occupancy
- **Alert engine** — Rule-based with severity levels, deduplication, multi-channel notifications
- **Business analytics** — Footfall, heatmaps, conversion rates, worker hours
- **VLM verification** — Scene understanding for complex event classification
- **Hardware abstraction** — Auto-selects optimal inference backend per device

## License

Apache-2.0 — see [LICENSE](LICENSE) for details.
