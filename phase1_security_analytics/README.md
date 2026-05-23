# Shopping Analytics Prototype - Phase 1

A production-ready, laptop-based people detection + tracking system for security and business analytics. Built for the HP Victus (RTX 30-series) but runs on any machine with Python + OpenCV.

## Features

- **Multi-Camera Support**: Connect IP webcams (phones), RTSP cameras, or local video files simultaneously
- **Real-Time Detection & Tracking**: RF-DETR (or mock mode) + ByteTrack for stable person IDs
- **Zone Analytics**: Define entrance lines, shelf polygons, checkout counters, and worker cabins
- **Event Logging**: Structured JSONL + SQLite database for dwell times, entry/exit, and no-purchase exits
- **Worker Identification**: Automatically classifies workers based on cabin dwell time
- **Business Metrics**: Footfall counting, conversion proxy, average dwell per zone, worker hours

## Quick Start

### 1. Install Dependencies

```bash
cd phase1_security_analytics
pip install -r requirements.txt
```

### 2. Configure Your Cameras

Edit `config.yaml`:

```yaml
cameras:
  - id: "phone_cam_01"
    # For Android: Install "IP Webcam" app, start server, use the HTTP URL
    source: "http://192.168.1.XX:8080/video"
    # For iOS: Use "EpocCam" or similar
    # For Real IP Cameras: Use RTSP URL
    # source: "rtsp://admin:password@192.168.1.YY:554/stream1"
    zones:
      - name: "entrance"
        type: "line"
        points: [[100, 500], [400, 500]]
      - name: "shelf_a"
        type: "polygon"
        points: [[500, 200], [700, 200], [700, 400], [500, 400]]
      - name: "checkout"
        type: "polygon"
        points: [[800, 400], [1000, 400], [1000, 600], [800, 600]]
      - name: "worker_cabin"
        type: "polygon"
        points: [[50, 50], [200, 50], [200, 200], [50, 200]]

model:
  type: "mock"  # Use "mock" for instant testing, "rfdetr" for real detection
```

### 3. Run the Pipeline

```bash
python src/main.py
```

- Events are logged to `data/events.jsonl` and `data/events.db`
- Press `Ctrl+C` to stop gracefully

### 4. View Analytics

```bash
cd analytics
jupyter lab daily_metrics.ipynb
```

Run the notebook cells to see:
- Total visitors and conversion rates
- Average dwell time per zone
- Worker cabin hours

## Architecture

```
phase1_security_analytics/
├── config.yaml              # Camera sources, zones, rules
├── requirements.txt         # Python dependencies
├── src/
│   ├── main.py             # Pipeline orchestrator
│   ├── camera_manager.py   # Multi-threaded frame capture
│   ├── detector.py         # RF-DETR or Mock detector
│   ├── tracker.py          # ByteTrack wrapper
│   ├── zone_engine.py      # Polygon/Line zone logic
│   ├── event_engine.py     # State machine for events
│   ├── logger.py           # JSONL + Text logging
│   └── db_manager.py       # SQLite storage
├── analytics/
│   └── daily_metrics.ipynb # Jupyter dashboard
└── data/                   # Auto-created: DB, logs
```

## Event Types

| Event Type | Description |
|------------|-------------|
| `person_entered_store` | Crossed entrance line into store |
| `person_exited_store` | Crossed exit line out of store |
| `dwell_start` / `dwell_end` | Entered/left a polygon zone |
| `no_purchase_exit` | Customer left without visiting checkout |
| `track_started` / `track_ended` | Detection track lifecycle |

## Using Your Phone as a Camera

### Android
1. Install **IP Webcam** by Pavel Khlebovich (free on Play Store)
2. Open the app, scroll to bottom, tap **Start Server**
3. Note the IP address shown (e.g., `http://192.168.1.5:8080`)
4. Use the `/video` endpoint in `config.yaml`

### iOS
1. Install **EpocCam** or **iVCam**
2. Follow app instructions to start streaming
3. Use the provided HTTP/RTSP URL in `config.yaml`

### Tips
- Keep your phone plugged in during operation
- Use 720p resolution for best performance on Wi-Fi
- Ensure your laptop and phone are on the same Wi-Fi network

## Switching to RF-DETR (Real Detection)

Once you've tested with mock mode:

1. Change `config.yaml`:
   ```yaml
   model:
     type: "rfdetr"
     size: "rfdetr-medium"
     confidence: 0.45
     device: "cuda"
   ```

2. Ensure you have GPU drivers installed
3. Run `python src/main.py` - the model will download automatically on first run

## Troubleshooting

- **"Failed to open stream"**: Check your camera IP, ensure it's on the same network
- **High latency**: The `CameraStream` class auto-flushes buffers; if still laggy, reduce camera resolution
- **No detections in mock mode**: Mock detector simulates 2 people moving horizontally; real detection requires RF-DETR setup
- **SQLite locked error**: Close any Jupyter notebooks or DB viewers before running the pipeline

## Next Steps (Phase 2)

- Add Streamlit dashboard for live metrics
- Generate heatmaps from dwell events
- Integrate with security alerting (email/SMS)
- Deploy as a Docker container

---

Built with ❤️ for retail security + business analytics.
