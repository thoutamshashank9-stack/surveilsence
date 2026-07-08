import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_system_health():
    with TestClient(app) as client:
        response = client.get("/api/v1/system/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

def test_cameras_list():
    with TestClient(app) as client:
        response = client.get("/api/v1/cameras", headers={"X-API-Key": "dev-secret-key-12345"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)

def test_alert_stats():
    with TestClient(app) as client:
        response = client.get("/api/v1/alerts/stats", headers={"X-API-Key": "dev-secret-key-12345"})
        assert response.status_code == 200
        assert "active_count" in response.json()
        assert "total" in response.json()
