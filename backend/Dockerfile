# Use official slim Python image
FROM python:3.12-slim-bookworm

# Prevent writing pyc files and enable buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for OpenCV and video streaming
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1 \
    libglib2.0-0 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirement manifests
COPY requirements/base.txt requirements/base.txt
COPY requirements/inference.txt requirements/inference.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements/base.txt -r requirements/inference.txt

# Copy source code
COPY . .

# Create directories for DB/logs/models
RUN mkdir -p data models/registry/detection

# Expose API port
EXPOSE 8000

# Run uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
