#!/bin/bash
# ==============================================================================
# Edge AI CCTV Analytics Platform — Raspberry Pi 5 + Hailo-8 Deployment Script
# ==============================================================================
set -euo pipefail

echo "========================================="
echo "Starting Raspberry Pi 5 Deployment"
echo "Target: Hailo-8 M.2 Acceleration Module"
echo "========================================="

# 1. Update OS Packages
echo "[1/6] Updating OS packages..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y dkms git python3-pip python3-venv ffmpeg libsm6 libxext6 \
  pkg-config libssl-dev libsrtp2-dev python3-dev build-essential

# 2. Install HailoRT PCIe Driver & Firmware
echo "[2/6] Setting up HailoRT driver repository..."
if ! command -v hailortcli &> /dev/null; then
  echo "Downloading HailoRT installer package..."
  # Fetch latest Raspberry Pi compatible HailoRT DKMS deb
  curl -L -o hailort-dkms.deb "https://hailo.ai/download/hailort/latest/hailort-dkms_all.deb" || true
  if [ -f hailort-dkms.deb ]; then
    sudo dpkg -i hailort-dkms.deb || sudo apt-get install -f -y
    rm hailort-dkms.deb
  else
    echo "Warning: HailoRT deb could not be fetched automatically. Please install it manually."
  fi
else
  echo "HailoRT tools already installed: $(hailortcli --version)"
fi

# 3. Create Python Virtual Environment
echo "[3/6] Configuring Python environment..."
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install --upgrade pip setuptools wheel

# Install base requirements
pip install -r backend/requirements/base.txt -r backend/requirements/inference.txt

# Install HailoRT python bindings wheel
echo "Installing HailoRT Python wheel..."
# On Raspberry Pi, the wheel is usually available in the local directory or from Hailo
# pip install /usr/share/hailort/hailort-*.whl || true

# Install aiortc for WebRTC streaming
echo "Installing aiortc..."
pip install aiortc

# 4. Create Models Directory & HEF symlinks
echo "[4/6] Setting up models registry..."
mkdir -p models/registry/detection
if [ ! -f models/registry/detection/rtdetrv2_r18.hef ]; then
  echo "Please compile your HEF model and place it at: models/registry/detection/rtdetrv2_r18.hef"
  echo "A simulated fallback will run if the file is absent."
fi

# 5. Create systemd Service Descriptors
echo "[5/6] Registering systemd service tasks..."

# Backend Service
sudo tee /etc/systemd/system/surveilsence-backend.service > /dev/null <<EOF
[Unit]
Description=Edge AI CCTV Analytics Platform Backend
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)/backend
ExecStart=$(pwd)/backend/venv/bin/python -m uvicorn app.main:app --port 8000 --host 0.0.0.0
Restart=always
RestartSec=5
Environment=ENV_FILE=.env

[Install]
WantedBy=multi-user.target
EOF

# Frontend Service (Build and serve using simple HTTP server, or run Vite preview)
sudo tee /etc/systemd/system/surveilsence-frontend.service > /dev/null <<EOF
[Unit]
Description=Edge AI CCTV Analytics Platform UI
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)/frontend
ExecStart=/usr/bin/npm run preview -- --host 0.0.0.0 --port 5173
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 6. Enable Services
echo "[6/6] Reloading systemd daemons and enabling services..."
sudo systemctl daemon-reload
sudo systemctl enable surveilsence-backend.service || true
sudo systemctl enable surveilsence-frontend.service || true

echo "========================================="
echo "Deployment scripts successfully written."
echo "Use 'sudo systemctl start surveilsence-backend' to launch backend service."
echo "========================================="
