import pytest
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.models.enums import EventType

@pytest.mark.asyncio
async def test_end_to_end_analytics_pipeline():
    """
    Test the E2E lifecycle:
    1. Verify system health.
    2. Register a new camera via REST API.
    3. Verify camera is listed and enabled.
    4. Query analytics endpoints for the new camera (expecting initial empty state).
    """
    with TestClient(app) as client:
        # 1. Verify health
        health_resp = client.get("/api/v1/system/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "healthy"
        
        # 2. Register a camera
        headers = {"X-API-Key": "dev-secret-key-12345"}
        client.delete("/api/v1/cameras/e2e_cam_01", headers=headers)
        camera_data = {
            "id": "e2e_cam_01",
            "name": "E2E Lobby Camera",
            "source": "mock",
            "type": "mock",
            "enabled": True,
            "stream_type": "main",
            "fps_cap": 30,
            "zones": [
                {
                    "name": "entrance_line",
                    "type": "line",
                    "points": [[100, 400], [500, 400]]
                },
                {
                    "name": "restricted_area",
                    "type": "polygon",
                    "points": [[10, 10], [100, 10], [100, 100], [10, 100]],
                    "restricted": True
                }
            ]
        }
        
        reg_resp = client.post("/api/v1/cameras", json=camera_data, headers=headers)
        assert reg_resp.status_code in [200, 201]
        
        # 3. Verify camera is listed
        list_resp = client.get("/api/v1/cameras", headers=headers)
        assert list_resp.status_code == 200
        cameras = list_resp.json()
        assert any(c["id"] == "e2e_cam_01" for c in cameras)
        
        # 4. Query Footfall Analytics (initial state)
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        footfall_resp = client.get(
            f"/api/v1/analytics/footfall?camera_id=e2e_cam_01&date={today_str}",
            headers=headers
        )
        assert footfall_resp.status_code == 200
        assert footfall_resp.json()["total_entries"] == 0
        
        # 5. Query Dwell Analytics (initial state)
        dwell_resp = client.get(
            f"/api/v1/analytics/dwell?camera_id=e2e_cam_01&date={today_str}",
            headers=headers
        )
        assert dwell_resp.status_code == 200
        assert len(dwell_resp.json()["zones"]) == 0
        
        # 6. Query Business Analytics (initial state)
        biz_resp = client.get(
            f"/api/v1/analytics/business?camera_id=e2e_cam_01&date={today_str}",
            headers=headers
        )
        assert biz_resp.status_code == 200
        assert biz_resp.json()["conversion_rate"] == 0.0
        assert biz_resp.json()["worker_hours"] == 0.0
