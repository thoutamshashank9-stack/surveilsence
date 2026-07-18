import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import get_api_key

def _auth_headers():
    return {"X-API-Key": get_api_key()}

def test_system_health():
    with TestClient(app) as client:
        response = client.get("/api/v1/system/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

def test_cameras_list():
    with TestClient(app) as client:
        response = client.get("/api/v1/cameras", headers=_auth_headers())
        assert response.status_code == 200
        assert isinstance(response.json(), list)

def test_alert_stats():
    with TestClient(app) as client:
        response = client.get("/api/v1/alerts/stats", headers=_auth_headers())
        assert response.status_code == 200
        assert "active_count" in response.json()
        assert "total" in response.json()

def test_detection_model_api():
    with TestClient(app) as client:
        # Test GET active detection model
        response = client.get("/api/v1/system/detection-model", headers=_auth_headers())
        assert response.status_code == 200
        data = response.json()
        assert "model" in data
        assert "model_path" in data
        assert "input_size" in data
        assert "confidence_threshold" in data

        # Test PUT switch to rtdetrv2_r18
        response = client.put(
            "/api/v1/system/detection-model",
            headers=_auth_headers(),
            json={"model": "rtdetrv2_r18", "confidence_threshold": 0.40}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["active_model"] == "rtdetrv2_r18"

        # Verify change
        response = client.get("/api/v1/system/detection-model", headers=_auth_headers())
        assert response.json()["model"] == "rtdetrv2_r18"
        assert response.json()["confidence_threshold"] == 0.40
        assert response.json()["input_size"] == [640, 640]

        # Test PUT switch to rfdetr_nano
        response = client.put(
            "/api/v1/system/detection-model",
            headers=_auth_headers(),
            json={"model": "rfdetr_nano", "confidence_threshold": 0.30}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["active_model"] == "rfdetr_nano"

        # Verify change
        response = client.get("/api/v1/system/detection-model", headers=_auth_headers())
        assert response.json()["model"] == "rfdetr_nano"
        assert response.json()["confidence_threshold"] == 0.30
        assert response.json()["input_size"] == [384, 384]

