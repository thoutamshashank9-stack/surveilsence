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
