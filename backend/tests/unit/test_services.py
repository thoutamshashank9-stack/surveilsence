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

class MockBehavioralRule:
    def __init__(self, enabled=True, **kwargs):
        self.enabled = enabled
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockBehavioralConfig:
    def __init__(self):
        self.unusual_activity = MockBehavioralRule(
            enabled=True, running_threshold_mps=2.5, crowd_min_count=3, crowd_radius_m=2.0, flow_direction_deg=0.0
        )
        self.velocity_loitering = MockBehavioralRule(
            enabled=True, dwell_threshold_seconds=2.0, velocity_threshold_mps=0.5
        )
        self.sweethearting = MockBehavioralRule(enabled=False)
        self.concealment = MockBehavioralRule(enabled=False)

class MockSettings:
    def __init__(self, camera_id="cam_test", zones=None, cameras=None):
        self.alerts = MockAlertsConfig()
        if cameras is not None:
            self.cameras = cameras
        elif camera_id:
            self.cameras = [MockCameraConfigItem(camera_id, zones)]
        else:
            self.cameras = []
        self.analytics = MockAnalyticsConfig()
        self.behavioral = MockBehavioralConfig()

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

def test_alert_manager_evaluate_frame():
    """Verify evaluate_frame interface as used by CameraWorker."""
    settings = MockSettings()
    alert_manager = AlertManager(settings)
    
    detections = sv.Detections.empty()
    detections.tracker_id = np.array([5])
    detections.class_id = np.array([0])
    crossings = [(5, "security_line", "in")]
    
    alerts = alert_manager.evaluate_frame(
        camera_id="cam_test",
        frame=None,
        tracked=detections,
        crossings=crossings,
        zone_states={"perimeter": {5}}
    )
    assert len(alerts) >= 1
    assert any(a["alert_type"] == "line_crossing" for a in alerts)

def test_alert_manager_loitering_time_based():
    """Verify dwell time based loitering detection."""
    settings = MockSettings()
    settings.alerts.loitering.threshold_seconds = 2
    settings.alerts.loitering.cooldown_seconds = 1
    alert_manager = AlertManager(settings)
    
    detections = sv.Detections.empty()
    detections.tracker_id = np.array([7])
    detections.class_id = np.array([0])
    
    # First frame enters zone: dwell timer initialized
    alerts1 = alert_manager.evaluate(
        camera_id="cam_test",
        detections=detections,
        zone_states={"restricted_vault": {7}},
        line_crossings=[]
    )
    assert len(alerts1) == 0
    
    # Simulate dwell by advancing the recorded dwell start time
    key = ("cam_test", "restricted_vault", 7)
    assert key in alert_manager.dwell_starts
    alert_manager.dwell_starts[key] -= 5.0  # 5 seconds in zone > 2s threshold
    
    alerts2 = alert_manager.evaluate(
        camera_id="cam_test",
        detections=detections,
        zone_states={"restricted_vault": {7}},
        line_crossings=[]
    )
    assert len(alerts2) == 1
    assert alerts2[0]["alert_type"] == "loitering"
    assert alerts2[0]["track_id"] == 7
    assert "loitering" in alerts2[0]["description"]

def test_alert_manager_dynamic_real_camera_intrusion():
    """Verify intrusion alerts fire for dynamic real cameras not in static YAML."""
    settings = MockSettings(cameras=[])
    assert settings.cameras == []
    alert_manager = AlertManager(settings)

    # Dynamic camera with restricted zone
    cam_cfg = MockCameraConfigItem(
        camera_id="phone_cam_real",
        zones=[MockCameraZoneConfig(name="restricted_vault", points=[[0,0],[100,0],[100,100],[0,100]], restricted=True)]
    )
    alert_manager.camera_configs["phone_cam_real"] = cam_cfg

    detections = sv.Detections.empty()
    detections.tracker_id = np.array([12])
    detections.class_id = np.array([0])
    detections.xyxy = np.array([[10, 10, 50, 50]])

    alerts = alert_manager.evaluate(
        camera_id="phone_cam_real",
        detections=detections,
        zone_states={"restricted_vault": {12}},
        line_crossings=[]
    )
    assert len(alerts) >= 1
    assert any(a["alert_type"] == "intrusion" and a["track_id"] == 12 for a in alerts)

def test_alert_manager_unusual_activity_rules_real_camera():
    """Verify unusual activity rules (running, fall, crowd, counterflow) on dynamic real camera."""
    settings = MockSettings(cameras=[])
    alert_manager = AlertManager(settings)

    # 1. Unusual Running
    det_run = sv.Detections.empty()
    det_run.tracker_id = np.array([3])
    det_run.class_id = np.array([0])
    det_run.xyxy = np.array([[10, 10, 50, 120]])

    # Move target rapidly across frames (> 2.5 m/s)
    alerts_run = []
    for i in range(4):
        det_run.xyxy = np.array([[10 + i * 200, 10, 50 + i * 200, 120]])
        res = alert_manager.evaluate("phone_cam_real", det_run, {}, [])
        alerts_run.extend(res)
    assert any(a["alert_type"] == "unusual_running" for a in alerts_run)

    # 2. Unusual Crowd Gathering
    det_crowd = sv.Detections.empty()
    det_crowd.tracker_id = np.array([10, 11, 12])
    det_crowd.class_id = np.array([0, 0, 0])
    det_crowd.xyxy = np.array([
        [100, 100, 140, 200],
        [110, 105, 150, 205],
        [105, 110, 145, 210]
    ])
    # Initial detection frame
    alert_manager.evaluate("phone_cam_real", det_crowd, {}, [])
    # Second frame triggers crowd gathering
    alerts_crowd = alert_manager.evaluate("phone_cam_real", det_crowd, {}, [])
    assert any(a["alert_type"] == "unusual_crowd_gathering" for a in alerts_crowd)

    # 3. Unusual Counterflow (movement opposing 0 deg flow)
    det_flow = sv.Detections.empty()
    det_flow.tracker_id = np.array([20])
    det_flow.class_id = np.array([0])
    det_flow.xyxy = np.array([[200, 100, 240, 200]])
    alert_manager.evaluate("phone_cam_real", det_flow, {}, [])

    # Step in counter direction (left: dx = -50, angle 180 deg vs 0 deg target)
    det_flow.xyxy = np.array([[150, 100, 190, 200]])
    alerts_flow = alert_manager.evaluate("phone_cam_real", det_flow, {}, [])
    assert any(a["alert_type"] == "unusual_counterflow" for a in alerts_flow)

def test_alert_manager_velocity_loitering_maintains_dwell_starts():
    """Verify dwell_starts is always populated when velocity loitering is enabled."""
    settings = MockSettings(cameras=[])
    settings.behavioral.velocity_loitering.enabled = True
    alert_manager = AlertManager(settings)

    det = sv.Detections.empty()
    det.tracker_id = np.array([99])
    det.class_id = np.array([0])
    det.xyxy = np.array([[20, 20, 60, 120]])

    alert_manager.evaluate("phone_cam_real", det, {"lobby_zone": {99}}, [])
    key = ("phone_cam_real", "lobby_zone", 99)
    assert key in alert_manager.dwell_starts
    assert alert_manager.dwell_starts[key] > 0

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
    
    # 4. Populate events for business conversion & worker hours
    db_session.add(Event(
        camera_id="cam_01",
        timestamp=datetime.utcnow() - timedelta(minutes=4),
        event_type=EventType.ZONE_EXIT,
        track_id=101,
        zone_name="checkout",
        duration_seconds=30.0
    ))
    db_session.add(Event(
        camera_id="cam_01",
        timestamp=datetime.utcnow() - timedelta(minutes=3),
        event_type=EventType.ZONE_EXIT,
        track_id=103,
        zone_name="worker_cabin",
        duration_seconds=7200.0  # 2 hours
    ))
    
    await db_session.commit()

    # 5. Query heatmap
    heatmap = await engine.get_heatmap_data(db_session, "cam_01", hours_ago=1)
    assert len(heatmap.points) == 1
    assert heatmap.points[0].x == 250.0
    assert heatmap.points[0].y == 350.0
    assert heatmap.points[0].intensity == 1.0

    # 6. Query business metrics
    biz = await engine.get_business_analytics(db_session, "cam_01", today_str)
    assert biz.conversion_rate == 100.0  # 1 checkout visitor / 1 entry = 100%
    assert biz.worker_hours == 2.0       # 7200s / 3600 = 2.0 hours
