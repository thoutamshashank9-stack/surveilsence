import pytest
import time
from app.ai.behavioral.unusual_activity import UnusualActivityClassifier

def test_unusual_activity_running_detection():
    classifier = UnusualActivityClassifier(running_threshold_mps=2.0)
    
    # 2 updates below threshold
    res1 = classifier.update(track_id=1, centroid=(100, 100), frame_timestamp=1.0, ema_velocity=1.5)
    assert res1 is None

    res2 = classifier.update(track_id=1, centroid=(110, 100), frame_timestamp=1.2, ema_velocity=2.5)
    assert res2 is None

    res3 = classifier.update(track_id=1, centroid=(120, 100), frame_timestamp=1.4, ema_velocity=2.6)
    assert res3 is None

    # 3rd consecutive fast update triggers alert
    res4 = classifier.update(track_id=1, centroid=(130, 100), frame_timestamp=1.6, ema_velocity=2.7)
    assert res4 is not None
    assert res4["event"] == "UNUSUAL_RUNNING"
    assert res4["track_id"] == 1
    assert "running" in res4["description"]

def test_unusual_activity_fall_detection():
    classifier = UnusualActivityClassifier()
    
    # Person standing tall: bbox = [100, 100, 140, 200] -> H=100, W=40, Aspect = 2.5
    standing_bbox = (100.0, 100.0, 140.0, 200.0)
    classifier.update(track_id=2, centroid=(120, 150), frame_timestamp=1.0, bbox=standing_bbox, ema_velocity=1.0)
    
    # Person collapses: bbox = [100, 180, 200, 210] -> H=30, W=100, Aspect = 0.3
    collapsed_bbox = (100.0, 180.0, 200.0, 210.0)
    
    # First frame of collapse candidate
    res1 = classifier.update(track_id=2, centroid=(150, 195), frame_timestamp=1.2, bbox=collapsed_bbox, ema_velocity=0.1)
    assert res1 is None
    
    # Second update > 1 sec later motionless
    res2 = classifier.update(track_id=2, centroid=(150, 195), frame_timestamp=2.5, bbox=collapsed_bbox, ema_velocity=0.1)
    assert res2 is not None
    assert res2["event"] == "UNUSUAL_FALL_DETECTED"
    assert res2["track_id"] == 2

def test_unusual_activity_crowd_gathering():
    classifier = UnusualActivityClassifier(crowd_min_count=3)
    
    all_centroids = {
        10: (100.0, 100.0),
        11: (110.0, 105.0),
        12: (105.0, 110.0)
    }
    
    classifier.update(track_id=10, centroid=(100.0, 100.0), frame_timestamp=1.0, all_centroids=all_centroids)
    res = classifier.update(track_id=10, centroid=(100.0, 100.0), frame_timestamp=2.0, all_centroids=all_centroids)
    assert res is not None
    assert res["event"] == "UNUSUAL_CROWD_GATHERING"

def test_unusual_activity_counterflow():
    # Expected flow direction: 0 degrees (moving right: dx > 0, dy = 0)
    classifier = UnusualActivityClassifier(flow_direction_deg=0.0)
    
    # Start at x=200
    classifier.update(track_id=5, centroid=(200.0, 100.0), frame_timestamp=1.0)
    
    # Move left (dx = -50, dy = 0) -> angle 180 deg (opposite of 0 deg)
    res = classifier.update(track_id=5, centroid=(150.0, 100.0), frame_timestamp=1.2)
    assert res is not None
    assert res["event"] == "UNUSUAL_COUNTERFLOW"
