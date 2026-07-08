import time
import asyncio
import threading
import numpy as np
from typing import Dict, List, Set, Tuple, Any, Optional
import supervision as sv

from app.config import CameraConfigItem, Settings
from app.models.enums import CameraStatus, EventType
from app.core.events import EventBus
from app.services.camera_manager import CameraManager
from app.services.inference_manager import InferenceManager
from app.services.tracking_manager import TrackingManager
from app.services.alert_manager import AlertManager
from app.services.vlm_service import VLMVerificationService
from app.ai.postprocessing.zone_rules import ZoneEngine
from app.core.logging import get_logger

logger = get_logger(__name__)

class CameraWorker:
    def __init__(
        self,
        config: CameraConfigItem,
        settings: Settings,
        event_bus: EventBus,
        camera_manager: CameraManager,
        inference_manager: InferenceManager,
        tracking_manager: TrackingManager,
        alert_manager: AlertManager
    ):
        self.config = config
        self.settings = settings
        self.event_bus = event_bus
        self.camera_manager = camera_manager
        self.inference_manager = inference_manager
        self.tracking_manager = tracking_manager
        self.alert_manager = alert_manager
        
        self.camera_id = config.id
        self.zone_engine = ZoneEngine(config.zones)
        self.vlm_service = VLMVerificationService()
        
        # Track position history for line crossing: track_id -> (last_x, last_y)
        self.last_positions: Dict[int, Tuple[float, float]] = {}
        
        # Tracks current zone occupancy: track_id -> set of zone names
        self.track_zones: Dict[int, Set[str]] = {}
        self.track_roles: Dict[int, str] = {}
        
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Camera processing worker started", camera_id=self.camera_id)

    def stop(self) -> None:
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        logger.info("Camera processing worker stopped", camera_id=self.camera_id)

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._async_run_loop())
        loop.close()

    async def _async_run_loop(self) -> None:
        frame_delay = 1.0 / self.config.fps_cap
        
        while self.running:
            start_time = time.time()
            
            # 1. Grab frame
            ret, frame = self.camera_manager.get_frame(self.camera_id)
            if not ret or frame is None:
                await asyncio.sleep(0.05)
                continue
                
            try:
                # 2. Run Inference
                detections = self.inference_manager.detect(frame)
                
                # 3. Run Tracking
                tracked = self.tracking_manager.update(self.camera_id, detections)
                
                # Publish frame analysis event (for web preview & UI stream)
                await self._publish_frame_analysis(tracked)
                
                # 4. Zone & Line Crossing Evaluation
                zone_states = self.zone_engine.evaluate_zones(tracked)
                line_crossings = self._evaluate_line_crossings(tracked)
                
                # 5. Zone transition events (Entry / Exit / Dwell)
                await self._evaluate_zone_transitions(zone_states)
                
                # 6. Evaluate Alerts
                alerts = self.alert_manager.evaluate(
                    camera_id=self.camera_id,
                    detections=tracked,
                    zone_states=zone_states,
                    line_crossings=line_crossings
                )
                
                # Emit alerts to database/event bus
                for alert in alerts:
                    if alert["alert_type"] in ["intrusion", "loitering"]:
                        asyncio.create_task(self._run_vlm_verification_and_publish(alert, frame.copy()))
                    else:
                        await self.event_bus.publish(EventType.ALERT, alert)

            except Exception as e:
                logger.error("Error in camera processing loop", camera_id=self.camera_id, error=str(e))
                
            # Frame rate throttle
            elapsed = time.time() - start_time
            sleep_time = max(0.001, frame_delay - elapsed)
            await asyncio.sleep(sleep_time)

    async def _publish_frame_analysis(self, tracked: sv.Detections) -> None:
        """Publish detections for frontend real-time tracking display."""
        CLASS_MAPPINGS = {
            0: "person",
            1: "vehicle",
            2: "vehicle",
            3: "vehicle",
            5: "vehicle",
            7: "vehicle",
            80: "fire",
            81: "smoke",
            82: "weapon",
            83: "PPE"
        }
        
        detections_list = []
        if tracked.tracker_id is not None:
            for idx, box in enumerate(tracked.xyxy):
                track_id = int(tracked.tracker_id[idx])
                class_id = int(tracked.class_id[idx])
                conf = float(tracked.confidence[idx])
                
                class_name = CLASS_MAPPINGS.get(class_id, "person")
                role = self.track_roles.get(track_id, "customer")
                
                # Anchor coordinates
                detections_list.append({
                    "track_id": track_id,
                    "class_id": class_id,
                    "class_name": class_name,
                    "role": role,
                    "confidence": conf,
                    "box": {
                        "x1": float(box[0]),
                        "y1": float(box[1]),
                        "x2": float(box[2]),
                        "y2": float(box[3])
                    }
                })
                
        # Emit detection frame events
        await self.event_bus.publish(
            EventType.DETECTION,
            {
                "camera_id": self.camera_id,
                "timestamp": time.time(),
                "tracked_objects": detections_list
            }
        )

    def _evaluate_line_crossings(self, tracked: sv.Detections) -> List[Tuple[int, str, str]]:
        crossings = []
        if tracked.tracker_id is None:
            return crossings
            
        for idx, box in enumerate(tracked.xyxy):
            track_id = int(tracked.tracker_id[idx])
            
            # Bottom center anchor
            cx = (box[0] + box[2]) / 2
            cy = box[3]
            
            curr_pos = (cx, cy)
            
            if track_id in self.last_positions:
                prev_pos = self.last_positions[track_id]
                # Check crossing
                line_crosses = self.zone_engine.check_line_crossings(track_id, prev_pos, curr_pos)
                for line_name, direction in line_crosses:
                    crossings.append((track_id, line_name, direction))
                    
                    # Async tasks shouldn't be created inside synchronous loop but we return it to alert evaluation
                    asyncio.create_task(
                        self.event_bus.publish(
                            EventType.LINE_CROSS,
                            {
                                "camera_id": self.camera_id,
                                "track_id": track_id,
                                "line_name": line_name,
                                "direction": direction,
                                "timestamp": time.time()
                            }
                        )
                    )
                    
            self.last_positions[track_id] = curr_pos
            
        # Clean up lost track positions
        active_ids = set(int(tid) for tid in tracked.tracker_id)
        for tid in list(self.last_positions.keys()):
            if tid not in active_ids:
                self.last_positions.pop(tid)
                
        return crossings

    async def _evaluate_zone_transitions(self, zone_states: Dict[str, Set[int]]) -> None:
        """Handle zone entry, exit and dwell tracking."""
        curr_time = time.time()
        
        # Build inverted map: track_id -> set of zone names currently in
        tracks_in_zones: Dict[int, Set[str]] = {}
        for zone_name, track_ids in zone_states.items():
            for track_id in track_ids:
                if track_id not in tracks_in_zones:
                    tracks_in_zones[track_id] = set()
                tracks_in_zones[track_id].add(zone_name)
                
        # 1. Check Entries & exits
        # Active tracks
        all_active_tracks = set(tracks_in_zones.keys())
        # All tracked states stored
        all_stored_tracks = set(self.track_zones.keys())
        
        # Entries: track is in a zone now, but wasn't before
        for track_id, current_zones in tracks_in_zones.items():
            prev_zones = self.track_zones.get(track_id, set())
            entries = current_zones - prev_zones
            
            for zone_name in entries:
                if zone_name == "worker_cabin":
                    self.track_roles[track_id] = "worker"
                await self.event_bus.publish(
                    EventType.ZONE_ENTRY,
                    {
                        "camera_id": self.camera_id,
                        "track_id": track_id,
                        "zone_name": zone_name,
                        "timestamp": curr_time
                    }
                )
                
        # Exits: track was in zone, but is not now
        for track_id in all_stored_tracks:
            prev_zones = self.track_zones[track_id]
            current_zones = tracks_in_zones.get(track_id, set())
            exits = prev_zones - current_zones
            
            for zone_name in exits:
                # Dwell time calculation
                dwell_start_key = (self.camera_id, zone_name, track_id)
                dwell_time = 0.0
                if hasattr(self.alert_manager, "dwell_starts"):
                    if dwell_start_key in self.alert_manager.dwell_starts:
                        dwell_time = curr_time - self.alert_manager.dwell_starts[dwell_start_key]

                await self.event_bus.publish(
                    EventType.ZONE_EXIT,
                    {
                        "camera_id": self.camera_id,
                        "track_id": track_id,
                        "zone_name": zone_name,
                        "duration_seconds": dwell_time,
                        "timestamp": curr_time
                    }
                )
                
        # Update state
        self.track_zones = tracks_in_zones

    async def _run_vlm_verification_and_publish(self, alert: dict, frame: np.ndarray) -> None:
        """Call VLM service asynchronously to prevent blocking the frame processing thread."""
        try:
            logger.info("Starting VLM verification for alert", alert_type=alert["alert_type"], track_id=alert.get("track_id"))
            desc = await self.vlm_service.verify_frame(
                frame=frame,
                alert_type=alert["alert_type"],
                zone_name=alert.get("zone_name") or "Area"
            )
            logger.info("VLM verification finished", description=desc)
            
            # Enrich alert metadata and description
            if "metadata_json" not in alert or alert["metadata_json"] is None:
                alert["metadata_json"] = {}
            alert["metadata_json"]["vlm_description"] = desc
            alert["description"] = f"{alert['description']} — {desc}"
        except Exception as e:
            logger.error("VLM verification task failed", error=str(e))
        finally:
            # Publish alert to the EventBus
            await self.event_bus.publish(EventType.ALERT, alert)
