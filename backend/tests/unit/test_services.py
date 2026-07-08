import time
import pytest
import numpy as np
import supervision as sv
from datetime import datetime, timedelta
from app.config import Settings
from app.services.alert_manager import AlertManager
from app.services.analytics_engine import AnalyticsEngine
from app.models.enums import AlertSeverity, EventType
from app.models.event import Event
from app.models.tracking import TrackCoordinate

# Mock settings class
class MockRuleConfig:
    def __init__(self, enabled=True, threshold_seconds=5, cooldown_seconds=10, severity="warning"):
        self.enabled = enabled
        self.threshold_seconds = threshold_seconds
        self.cooldown_seconds = cooldown_seconds
        self.severity = severity
        self.lines = None
        self.zones = None

class MockAlertsConfig:
    def __init__(self):
        self.intrusion = MockRuleConfig(severity="critical")
        self.loitering = MockRuleConfig(threshold_seconds=1)
        self.line_crossing = MockRuleConfig(cooldown_seconds=1)
        self.dwell_no_checkout = MockRuleConfig()

class MockCameraZoneConfig:
    def __init__(self, name, points, restricted=False):
        self.name = name
        self.points = points
        self.type = "polygon"
        self.restricted = restricted
        self.direction = None

    def model_dump(self):
        return {"name": self.name, "type": self.type, "points": self.points, "restricted": self.restricted}

class MockCameraConfigItem:
    def __init__(self, camera_id="cam_test", zones=None):
        self.id = camera_id
        self.name = "Test Camera"
        self.source = "mock"
        self.type = "mock"
        self.enabled = True
        self.stream_type = "sub"
        self.fps_cap = 30
        self.zones = zones or []

class MockAnalyticsConfig:
    def __init__(self):
        self.heatmap_resolution = [64, 48]

class MockSettings:
    def __init__(self, camera_id="cam_test", zones=None):
        self.alerts = MockAlertsConfig()
        self.cameras = [MockCameraConfigItem(camera_id, zones)]
        self.analytics = MockAnalyticsConfig()

def test_alert_manager_evaluation():
    settings = MockSettings()
    alert_manager = AlertManager(settings)
    
    # 1. Setup mock line crossing
    # crossings is list of (track_id, line_name, direction)
    crossings = [(1, "entrance_line", "in")]
    
    # Empty detections
    detections = sv.Detections.empty()
    detections.tracker_id = np.array([1])
    detections.class_id = np.array([0])
    
    alerts = alert_manager.evaluate(
        camera_id="cam_test",
        detections=detections,
        zone_states={},
        line_crossings=crossings
    )
    
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "line_crossing"
    assert alerts[0]["track_id"] == 1
    assert "entrance_line" in alerts[0]["description"]

def test_alert_manager_safety_rule():
    settings = MockSettings()
    alert_manager = AlertManager(settings)
    
    # Fire class ID is 80
    detections = sv.Detections(
        xyxy=np.array([[10, 10, 50, 50]], dtype=np.float32),
        confidence=np.array([0.95], dtype=np.float32),
        class_id=np.array([80], dtype=np.int32)
    )
    detections.tracker_id = np.array([42])
    
    alerts = alert_manager.evaluate(
        camera_id="cam_test",
        detections=detections,
        zone_states={},
        line_crossings=[]
    )
    
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "safety"
    assert alerts[0]["severity"] == "critical"
    assert "Fire" in alerts[0]["description"]

@pytest.mark.asyncio
async def test_analytics_engine_queries(db_session):
    # Setup analytics engine with test settings
    settings = MockSettings("cam_01")
    engine = AnalyticsEngine(settings)
    
    # 0. Populate camera
    from app.models.camera import Camera
    db_session.add(Camera(
        id="cam_01",
        name="Test Camera",
        source="mock",
        type="mock",
        enabled=True,
        status="online",
        config_json={"zones": []}
    ))

    # 1. Populate database events for footfall
    db_session.add(Event(
        camera_id="cam_01",
        timestamp=datetime.utcnow() - timedelta(minutes=10),
        event_type=EventType.LINE_CROSS,
        track_id=101,
        zone_name="entrance_line",
        metadata_json={"direction": "in"}
    ))
    db_session.add(Event(
        camera_id="cam_01",
        timestamp=datetime.utcnow() - timedelta(minutes=5),
        event_type=EventType.LINE_CROSS,
        track_id=102,
        zone_name="entrance_line",
        metadata_json={"direction": "out"}
    ))
    
    # 2. Populate track coordinates for heatmap
    db_session.add(TrackCoordinate(
        track_id=101,
        camera_id="cam_01",
        timestamp=datetime.utcnow() - timedelta(minutes=2),
        x=250.0,
        y=350.0,
        zone_name="lobby"
    ))
    
    await db_session.commit()
    
    # 3. Query footfall
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    footfall = await engine.get_footfall(db_session, "cam_01", today_str)
    assert footfall.total_entries == 1
    assert footfall.total_exits == 1
    
    # 4. Query heatmap
    heatmap = await engine.get_heatmap_data(db_session, "cam_01", hours_ago=1)
    assert len(heatmap.points) == 1
    assert heatmap.points[0].x == 250.0
    assert heatmap.points[0].y == 350.0
    assert heatmap.points[0].intensity == 1.0
