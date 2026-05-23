# QUICKSTART: Shopping Analytics Phase 1

Get running in **4 steps** with your phone as a camera.

---

## Step 1: Install Dependencies (2 minutes)

```bash
cd phase1_security_analytics
pip install -r requirements.txt
```

> **Note**: If you get errors installing `supervision` or `torch`, ensure you have Python 3.10+ and pip updated:
> ```bash
> python -m pip install --upgrade pip
> ```

---

## Step 2: Set Up Your Phone Camera (3 minutes)

### Android Users:
1. Download **"IP Webcam"** from Play Store (free, by Pavel Khlebovich)
2. Open the app → Scroll to bottom → Tap **"Start Server"**
3. You'll see an IP address like: `http://192.168.1.5:8080`
4. Write down this IP!

### iOS Users:
1. Download **"EpocCam"** from App Store
2. Follow the app's setup to start streaming
3. Note the HTTP/RTSP URL provided

### Important:
- Keep your phone **plugged into power** during use
- Ensure your laptop and phone are on the **same Wi-Fi network**

---

## Step 3: Configure & Test (1 minute)

Open `config.yaml` and update the `source` line with your phone's IP:

```yaml
cameras:
  - id: "phone_cam_01"
    source: "http://YOUR_PHONE_IP:8080/video"  # ← Change this!
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
  type: "mock"  # ← Start with "mock" to test instantly!
```

> **Why mock mode?** It simulates 2 people moving across the screen so you can test the entire pipeline immediately without downloading AI models. Once everything works, change this to `"rfdetr"` for real person detection.

---

## Step 4: Run the Pipeline! 🚀

```bash
python src/main.py
```

You should see logs like:
```
2024-01-15 10:30:00 [INFO] EventLogger: 🚀 Starting Shopping Analytics Pipeline...
2024-01-15 10:30:01 [INFO] CameraStream: [phone_cam_01] Connecting to http://...
2024-01-15 10:30:02 [INFO] CameraStream: [phone_cam_01] Successfully connected.
```

Let it run for 30 seconds, then press **`Ctrl+C`** to stop.

---

## Step 5: View Your Analytics 📊

```bash
cd analytics
jupyter lab daily_metrics.ipynb
```

In Jupyter:
1. Click each cell and press **Shift+Enter** to run
2. See your footfall, dwell times, and worker analytics!

---

## What's Next?

### A. Switch to Real Detection (RF-DETR)
Once mock mode works:
1. Edit `config.yaml`:
   ```yaml
   model:
     type: "rfdetr"
   ```
2. Run again – the model downloads automatically (~2 GB)
3. Point your camera at a real space with people!

### B. Add More Cameras
Add another entry in `config.yaml`:
```yaml
cameras:
  - id: "phone_cam_01"
    source: "http://192.168.1.5:8080/video"
    zones: [...]
    
  - id: "rtsp_cam_02"
    source: "rtsp://admin:pass@192.168.1.10:554/stream1"
    zones: [...]
```

### C. Customize Zones
The `points` in `config.yaml` are pixel coordinates `[x, y]`. To find exact coordinates for your camera:
1. Run the pipeline with mock mode
2. Uncomment the visualization lines in `src/main.py`
3. A window will show your video feed – note coordinates visually

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Failed to open stream" | Double-check IP, ensure same Wi-Fi, try opening the URL in a browser |
| No events in logs | Mock mode needs ~30 sec to simulate movement; wait longer |
| Jupyter won't open | Run `pip install jupyterlab` |
| SQLite locked error | Close Jupyter before running `main.py` |

---

**🎉 You're done!** You now have a working security + business analytics prototype.

For full documentation, see [README.md](README.md).
