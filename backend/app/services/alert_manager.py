import time
from typing import Dict, List, Set, Tuple, Any, Optional
from shapely.geometry import Polygon, Point, LineString
import supervision as sv

from app.config import Settings
from app.models.enums import AlertSeverity, AlertStatus, EventType
from app.core.logging import get_logger
from app.ai.postprocessing.homography import HomographyCalibrator
from app.ai.postprocessing.velocity_tracker import VelocityTracker
from app.ai.behavioral.sweethearting import SweetheartingClassifier
from app.ai.behavioral.concealment import ConcealmentClassifier
from app.ai.behavioral.velocity_loitering import VelocityGatedLoiteringClassifier

logger = get_logger(__name__)

class AlertManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Cooldown track: (camera_id, alert_type, track_id) -> timestamp
        self.cooldowns: Dict[Tuple[str, str, Optional[int]], float] = {}
        
        # Track entry timestamps for loitering: (camera_id, zone_name, track_id) -> timestamp
        self.dwell_starts: Dict[Tuple[str, str, int], float] = {}

        # Phase 9: Behavioral classifiers, lazy initialized per camera
        self.sweethearting_classifiers: Dict[str, SweetheartingClassifier] = {}
        self.velocity_trackers: Dict[str, VelocityTracker] = {}
        self.velocity_loitering_classifiers: Dict[str, VelocityGatedLoiteringClassifier] = {}
        self.concealment_classifiers: Dict[str, ConcealmentClassifier] = {}
        self.camera_configs: Dict[str, Any] = {}

    def _init_camera_classifiers(self, camera_id: str, cam_cfg: Optional[Any] = None) -> None:
        """
        Lazily initialize homography, velocity tracking, and behavioral classifiers
        for a camera feed from its database/profile configuration.
        """
        if camera_id in self.sweethearting_classifiers:
            return

        if cam_cfg is not None:
            self.camera_configs[camera_id] = cam_cfg
        else:
            cam_cfg = self.camera_configs.get(camera_id)

        if not cam_cfg:
            # Find camera config using safe getattr from static settings
            cameras = getattr(self.settings, "cameras", [])
            for c in cameras:
                if getattr(c, "id", None) == camera_id:
                    cam_cfg = c
                    self.camera_configs[camera_id] = cam_cfg
                    break

        if not cam_cfg:
            logger.warning("No settings configuration found for camera, skipping behavioral initialization", camera_id=camera_id)
            return

        # 1. Initialize Homography Calibrator (safe checks)
        h_calib = None
        homography_cfg = getattr(cam_cfg, "homography", None)
        if homography_cfg and getattr(homography_cfg, "enabled", False):
            h_calib = HomographyCalibrator(
                pixel_points=getattr(homography_cfg, "pixel_points", []),
                world_points=getattr(homography_cfg, "world_points", [])
            )

        # 2. Initialize Velocity Tracker
        v_tracker = VelocityTracker(homography=h_calib)
        self.velocity_trackers[camera_id] = v_tracker

        # 3. Find conveyor and bagging zones for sweethearting
        conveyor_poly = None
        bagging_poly = None
        
        behavioral_cfg = getattr(self.settings, "behavioral", None)
        sweet_cfg = getattr(behavioral_cfg, "sweethearting", None) if behavioral_cfg else None
        conveyor_zone_name = getattr(sweet_cfg, "conveyor_zone", "conveyor") if sweet_cfg else "conveyor"
        bagging_zone_name = getattr(sweet_cfg, "bagging_zone", "bagging") if sweet_cfg else "bagging"
        time_threshold = getattr(sweet_cfg, "time_threshold", 3.0) if sweet_cfg else 3.0
        
        zones = getattr(cam_cfg, "zones", [])
        for z in zones:
            z_name = getattr(z, "name", None)
            z_points = getattr(z, "points", [])
            if z_name == conveyor_zone_name and len(z_points) >= 3:
                conveyor_poly = Polygon(z_points)
            elif z_name == bagging_zone_name and len(z_points) >= 3:
                bagging_poly = Polygon(z_points)

        # Initialize Sweethearting Classifier
        if conveyor_poly and bagging_poly:
            self.sweethearting_classifiers[camera_id] = SweetheartingClassifier(
                conveyor_poly=conveyor_poly,
                bagging_poly=bagging_poly,
                time_threshold=time_threshold
            )
            logger.info("Initialized Sweethearting behavioral classifier", camera_id=camera_id)
        else:
            # Create a mock/empty classifier mapping to center of the frame as fallback
            mock_poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
            self.sweethearting_classifiers[camera_id] = SweetheartingClassifier(
                conveyor_poly=mock_poly,
                bagging_poly=mock_poly
            )

        # 4. Initialize Velocity Gated Loitering Classifier
        # Find restricted zones polygon to gate loitering checks
        loiter_poly = None
        for z in zones:
            if getattr(z, "restricted", False):
                z_points = getattr(z, "points", [])
                if len(z_points) >= 3:
                    loiter_poly = Polygon(z_points)
                    break

        loiter_cfg = getattr(behavioral_cfg, "velocity_loitering", None) if behavioral_cfg else None
        dwell_threshold = getattr(loiter_cfg, "dwell_threshold_seconds", 30.0) if loiter_cfg else 30.0
        velocity_threshold = getattr(loiter_cfg, "velocity_threshold_mps", 0.2) if loiter_cfg else 0.2

        self.velocity_loitering_classifiers[camera_id] = VelocityGatedLoiteringClassifier(
            dwell_threshold_seconds=dwell_threshold,
            velocity_threshold_mps=velocity_threshold,
            zone_polygon=loiter_poly
        )

        # 5. Initialize Concealment Classifier
        conceal_cfg = getattr(behavioral_cfg, "concealment", None) if behavioral_cfg else None
        proximity_threshold = getattr(conceal_cfg, "proximity_threshold", 0.3) if conceal_cfg else 0.3

        self.concealment_classifiers[camera_id] = ConcealmentClassifier(
            proximity_threshold=proximity_threshold,
            settings=self.settings
        )
        logger.info("Initialized velocity loitering and concealment classifiers", camera_id=camera_id)

    def register_pos_scan(self, camera_id: str, timestamp: float, upc: str) -> None:
        """
        Public webhook integration to route cash register scan events.
        """
        self._init_camera_classifiers(camera_id)
        classifier = self.sweethearting_classifiers.get(camera_id)
        if classifier:
            classifier.register_pos_scan(timestamp, upc)

    def evaluate(
        self,
        camera_id: str,
        detections: sv.Detections,
        zone_states: Dict[str, Set[int]],
        line_crossings: List[Tuple[int, str, str]],  # list of (track_id, line_name, direction)
        frame: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate alert rules and retail behavioral classifiers against current frame state.
        Returns a list of triggered alerts.
        """
        self._init_camera_classifiers(camera_id)
        behavioral_cfg = getattr(self.settings, "behavioral", None)
        triggered_alerts = []
        curr_time = time.time()
        
        # Helper: check cooldown
        def in_cooldown(alert_type: str, track_id: Optional[int], cooldown_s: int) -> bool:
            key = (camera_id, alert_type, track_id)
            if key in self.cooldowns:
                if curr_time - self.cooldowns[key] < cooldown_s:
                    return True
            return False

        def trigger_alert(alert_type: str, severity: str, track_id: Optional[int], zone_name: Optional[str], desc: str, metadata: dict = None) -> None:
            self.cooldowns[(camera_id, alert_type, track_id)] = curr_time
            triggered_alerts.append({
                "camera_id": camera_id,
                "alert_type": alert_type,
                "severity": severity,
                "track_id": track_id,
                "zone_name": zone_name,
                "description": desc,
                "metadata_json": metadata or {},
                "timestamp": curr_time
            })

        # 1. Evaluate Line Crossings
        alerts_cfg = getattr(self.settings, "alerts", None)
        line_config = getattr(alerts_cfg, "line_crossing", None) if alerts_cfg else None
        
        if line_config and getattr(line_config, "enabled", False):
            for track_id, line_name, direction in line_crossings:
                if getattr(line_config, "lines", None) is None or line_name in line_config.lines:
                    if not in_cooldown("line_crossing", track_id, line_config.cooldown_seconds):
                        desc = f"Object P{track_id} crossed {line_name} ({direction})"
                        trigger_alert(
                            alert_type="line_crossing",
                            severity=line_config.severity,
                            track_id=track_id,
                            zone_name=line_name,
                            desc=desc,
                            metadata={"direction": direction}
                        )

        # 2. Evaluate Zone-based Intrusion and Velocity-Gated Loitering
        v_tracker = self.velocity_trackers.get(camera_id)
        loiter_classifier = self.velocity_loitering_classifiers.get(camera_id)
        sweet_classifier = self.sweethearting_classifiers.get(camera_id)
        conceal_classifier = self.concealment_classifiers.get(camera_id)

        # Process velocity updates for active track bounding boxes
        active_track_velocities = {}
        if detections.tracker_id is not None and v_tracker:
            for idx, bbox in enumerate(detections.xyxy):
                track_id = int(detections.tracker_id[idx])
                # Bottom center coordinate
                bx = (bbox[0] + bbox[2]) / 2.0
                by = bbox[3]
                
                # Update velocity state
                vel = v_tracker.update(track_id, bx, by, curr_time)
                active_track_velocities[track_id] = vel

        for zone_name, track_ids in zone_states.items():
            # Get zone properties
            is_restricted = False
            cameras = getattr(self.settings, "cameras", [])
            for cam_cfg in cameras:
                if getattr(cam_cfg, "id", None) == camera_id:
                    zones = getattr(cam_cfg, "zones", [])
                    for z_cfg in zones:
                        if getattr(z_cfg, "name", None) == zone_name:
                            is_restricted = getattr(z_cfg, "restricted", False)
                            break

            # Intrusion detection
            intrusion_config = getattr(alerts_cfg, "intrusion", None) if alerts_cfg else None
            if intrusion_config and getattr(intrusion_config, "enabled", False) and is_restricted:
                for track_id in track_ids:
                    if not in_cooldown("intrusion", track_id, intrusion_config.cooldown_seconds):
                        desc = f"Unauthorized intrusion by P{track_id} in restricted zone '{zone_name}'"
                        trigger_alert(
                            alert_type="intrusion",
                            severity=intrusion_config.severity,
                            track_id=track_id,
                            zone_name=zone_name,
                            desc=desc
                        )

            # Evaluate loitering rules
            loiter_config = getattr(alerts_cfg, "loitering", None) if alerts_cfg else None
            if loiter_config and getattr(loiter_config, "enabled", False):
                for track_id in track_ids:
                    # Ground plane velocity computed in Phase 8
                    vel = active_track_velocities.get(track_id, 0.0)

                    # Trigger velocity-gated loitering classifier (Phase 9)
                    behavioral_cfg = getattr(self.settings, "behavioral", None)
                    vloiter_cfg = getattr(behavioral_cfg, "velocity_loitering", None) if behavioral_cfg else None
                    
                    if loiter_classifier and vloiter_cfg and getattr(vloiter_cfg, "enabled", False):
                        # Bottom middle
                        bx = (detections.xyxy[0][0] + detections.xyxy[0][2]) / 2.0 if len(detections) > 0 else 0.0
                        by = detections.xyxy[0][3] if len(detections) > 0 else 0.0
                        
                        anomaly = loiter_classifier.update(
                            track_id=track_id,
                            centroid=(bx, by),
                            frame_timestamp=curr_time,
                            ema_velocity=vel
                        )
                        if anomaly and not in_cooldown("loitering", track_id, loiter_config.cooldown_seconds):
                            trigger_alert(
                                alert_type="loitering",
                                severity=loiter_config.severity,
                                track_id=track_id,
                                zone_name=zone_name,
                                desc=anomaly["description"],
                                metadata={"dwell_time_seconds": curr_time - loiter_classifier.dwell_starts.get(track_id, curr_time), "velocity_mps": vel}
                            )
                    else:
                        # Standard simple dwell loitering fallback
                        key = (camera_id, zone_name, track_id)
                        if key not in self.dwell_starts:
                            self.dwell_starts[key] = curr_time
                        else:
                            dwell_time = curr_time - self.dwell_starts[key]
                            thresh = getattr(loiter_config, "threshold_seconds", 60) or 60
                            if dwell_time >= thresh:
                                if not in_cooldown("loitering", track_id, loiter_config.cooldown_seconds):
                                    desc = f"Object P{track_id} loitering in '{zone_name}' for {int(dwell_time)}s"
                                    trigger_alert(
                                        alert_type="loitering",
                                        severity=loiter_config.severity,
                                        track_id=track_id,
                                        zone_name=zone_name,
                                        desc=desc,
                                        metadata={"dwell_time_seconds": dwell_time}
                                    )

        # 3. Evaluate Cashier Sweethearting Anomalies
        sweet_cfg = getattr(behavioral_cfg, "sweethearting", None) if behavioral_cfg else None
        if sweet_classifier and sweet_cfg and getattr(sweet_cfg, "enabled", False) and detections.tracker_id is not None:
            for idx, bbox in enumerate(detections.xyxy):
                track_id = int(detections.tracker_id[idx])
                bx = (bbox[0] + bbox[2]) / 2.0
                by = bbox[3]
                
                # Check for sweethearting scan bypass
                anomaly = sweet_classifier.update(track_id, (bx, by), curr_time)
                if anomaly and not in_cooldown("sweethearting", track_id, 30):
                    trigger_alert(
                        alert_type="sweethearting",
                        severity="warning",
                        track_id=track_id,
                        zone_name="checkout",
                        desc=anomaly["description"]
                    )

        # 4. Evaluate Hand-to-Body Keypoint Concealment Anomalies
        conceal_cfg = getattr(behavioral_cfg, "concealment", None) if behavioral_cfg else None
        if conceal_classifier and conceal_cfg and getattr(conceal_cfg, "enabled", False) and detections.tracker_id is not None:
            # Check if keypoints are exposed in detections attributes
            keypoints_batch = getattr(detections, "keypoints", None)
            
            for idx, bbox in enumerate(detections.xyxy):
                track_id = int(detections.tracker_id[idx])
                bx = (bbox[0] + bbox[2]) / 2.0
                by = bbox[3]
                
                keypoints = keypoints_batch[idx] if keypoints_batch is not None and idx < len(keypoints_batch) else None
                # Simulated product disappearance for mock validation
                product_disappeared = (int(curr_time) % 20) == 0

                anomaly = conceal_classifier.update(
                    track_id=track_id,
                    centroid=(bx, by),
                    frame_timestamp=curr_time,
                    keypoints=keypoints,
                    product_disappeared=product_disappeared,
                    frame=frame,
                    bbox=bbox
                )
                if anomaly and not in_cooldown("concealment", track_id, 30):
                    trigger_alert(
                        alert_type="concealment",
                        severity="critical",
                        track_id=track_id,
                        zone_name="aisle",
                        desc=anomaly["description"]
                    )

        # Clean up loitering dwell starts
        active_keys = set()
        for zone_name, track_ids in zone_states.items():
            for track_id in track_ids:
                active_keys.add((camera_id, zone_name, track_id))
        for key in list(self.dwell_starts.keys()):
            if key[0] == camera_id and key not in active_keys:
                self.dwell_starts.pop(key)

        # 5. Evaluate Safety / Threat Detections
        if detections.tracker_id is not None:
            for idx, class_id in enumerate(detections.class_id):
                track_id = int(detections.tracker_id[idx])
                if class_id == 80:  # Fire
                    if not in_cooldown("fire_detected", track_id, 300):
                        trigger_alert("safety", "critical", track_id, "camera_field", "CRITICAL SAFETY THREAT: Fire detected in viewport!")
                elif class_id == 81:  # Smoke
                    if not in_cooldown("smoke_detected", track_id, 300):
                        trigger_alert("safety", "critical", track_id, "camera_field", "CRITICAL SAFETY THREAT: Smoke detected in viewport!")
                elif class_id == 82:  # Weapon
                    if not in_cooldown("weapon_detected", track_id, 300):
                        trigger_alert("safety", "critical", track_id, "camera_field", "SECURITY THREAT: Weapon detected in viewport!")

        # Perform periodic cleanup of old states
        if v_tracker:
            v_tracker.cleanup()
        if loiter_classifier:
            loiter_classifier.cleanup()
        if sweet_classifier:
            sweet_classifier.cleanup()
        if conceal_classifier:
            conceal_classifier.cleanup()

        for key, ts in list(self.cooldowns.items()):
            if curr_time - ts > 86400:
                self.cooldowns.pop(key)

        return triggered_alerts
