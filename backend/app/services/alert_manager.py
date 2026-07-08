import time
from typing import Dict, List, Set, Tuple, Any, Optional
import supervision as sv
from app.config import Settings
from app.models.enums import AlertSeverity, AlertStatus, EventType
from app.core.logging import get_logger

logger = get_logger(__name__)

class AlertManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Cooldown track: (camera_id, alert_type, track_id) -> timestamp
        self.cooldowns: Dict[Tuple[str, str, Optional[int]], float] = {}
        
        # Track entry timestamps for loitering: (camera_id, zone_name, track_id) -> timestamp
        self.dwell_starts: Dict[Tuple[str, str, int], float] = {}

    def evaluate(
        self,
        camera_id: str,
        detections: sv.Detections,
        zone_states: Dict[str, Set[int]],
        line_crossings: List[Tuple[int, str, str]]  # list of (track_id, line_name, direction)
    ) -> List[Dict[str, Any]]:
        """
        Evaluate alert rules against current frame state.
        Returns a list of triggered alerts.
        """
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
        line_config = self.settings.alerts.line_crossing
        if line_config.enabled:
            for track_id, line_name, direction in line_crossings:
                # Check if this line should alert
                if line_config.lines is None or line_name in line_config.lines:
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

        # Build list of active track IDs in zones
        # Track active zones to handle loitering state transitions
        for zone_name, track_ids in zone_states.items():
            # Get zone properties
            # Find if zone is restricted
            is_restricted = False
            for cam_cfg in self.settings.cameras:
                if cam_cfg.id == camera_id:
                    for z_cfg in cam_cfg.zones:
                        if z_cfg.name == zone_name:
                            is_restricted = z_cfg.restricted
                            break

            # 2. Evaluate Intrusions (Entry into restricted zones)
            intrusion_config = self.settings.alerts.intrusion
            if intrusion_config.enabled and is_restricted:
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

            # 3. Evaluate Loitering (Spent > threshold seconds in zone)
            loiter_config = self.settings.alerts.loitering
            if loiter_config.enabled:
                for track_id in track_ids:
                    key = (camera_id, zone_name, track_id)
                    
                    if key not in self.dwell_starts:
                        self.dwell_starts[key] = curr_time
                    else:
                        dwell_time = curr_time - self.dwell_starts[key]
                        thresh = loiter_config.threshold_seconds or 60
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

        # Clean up dwell_starts for tracks that exited the zones
        # If key is in dwell_starts but track_id is not in zone_states[zone_name]
        active_keys = set()
        for zone_name, track_ids in zone_states.items():
            for track_id in track_ids:
                active_keys.add((camera_id, zone_name, track_id))
                
        for key in list(self.dwell_starts.keys()):
            if key[0] == camera_id and key not in active_keys:
                self.dwell_starts.pop(key)

        # 4. Evaluate Safety / Threat Detections
        if detections.tracker_id is not None:
            for idx, class_id in enumerate(detections.class_id):
                track_id = int(detections.tracker_id[idx])
                if class_id == 80:  # Fire
                    if not in_cooldown("fire_detected", track_id, 300):
                        trigger_alert(
                            alert_type="safety",
                            severity="critical",
                            track_id=track_id,
                            zone_name="camera_field",
                            desc=f"CRITICAL SAFETY THREAT: Fire detected in viewport!"
                        )
                elif class_id == 81:  # Smoke
                    if not in_cooldown("smoke_detected", track_id, 300):
                        trigger_alert(
                            alert_type="safety",
                            severity="critical",
                            track_id=track_id,
                            zone_name="camera_field",
                            desc=f"CRITICAL SAFETY THREAT: Smoke detected in viewport!"
                        )
                elif class_id == 82:  # Weapon
                    if not in_cooldown("weapon_detected", track_id, 300):
                        trigger_alert(
                            alert_type="safety",
                            severity="critical",
                            track_id=track_id,
                            zone_name="camera_field",
                            desc=f"SECURITY THREAT: Weapon detected in viewport!"
                        )

        # Periodic cleanup of old cooldown keys (older than 24 hours) to prevent memory leak
        for key, ts in list(self.cooldowns.items()):
            if curr_time - ts > 86400:
                self.cooldowns.pop(key)

        return triggered_alerts
