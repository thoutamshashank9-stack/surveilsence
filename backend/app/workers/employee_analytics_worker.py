import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional, Set
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database import AsyncSessionLocal
from app.core.events import EventBus
from app.models.enums import EventType
from app.models.employee_analytics import StaffShift, StaffInteraction
from app.models.camera import Camera
from app.ai.postprocessing.homography import HomographyCalibrator
from app.core.logging import get_logger

logger = get_logger(__name__)

class EmployeeAnalyticsWorker:
    def __init__(self, settings: Settings, event_bus: EventBus):
        self.settings = settings
        self.event_bus = event_bus
        
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.lock = asyncio.Lock()
        
        # Homography calibrators per camera
        self.calibrators: Dict[str, HomographyCalibrator] = {}
        
        # Active shifts: employee_id -> dict state
        # Dict details: camera_id, track_id, first_seen, last_seen, last_seen_tick, total_presence_seconds, total_break_seconds, total_idle_seconds, in_cabin, cabin_exit_time
        self.active_shifts: Dict[str, Dict[str, Any]] = {}
        
        # Active interactions: (employee_id, customer_track_id) -> dict state
        # Dict details: start_time, last_seen, camera_id
        self.active_interactions: Dict[Tuple[str, int], Dict[str, Any]] = {}
        
        # POS transaction scans buffer: list of dicts (timestamp, employee_id, camera_id, ticket_id)
        self.pos_transactions: List[Dict[str, Any]] = []
        
        # Cache for DB camera employee assignments
        self.camera_employee_cache: Dict[str, Dict[str, Any]] = {}

    async def start(self) -> None:
        if self.running:
            return
        self.running = True
        
        # 1. Initialize Homography Calibrators from database cameras
        await self._load_camera_calibrations()
        await self._load_camera_employee_mappings()
        
        # 2. Subscribe to Event Bus
        self.event_bus.subscribe(EventType.DETECTION, self.process_detection)
        self.event_bus.subscribe(EventType.ZONE_ENTRY, self.process_zone_entry)
        
        # 3. Start cleanup worker loop for stale shifts/interactions
        self.task = asyncio.create_task(self._cleanup_loop())
        logger.info("Employee Analytics Worker started")


    async def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        # Save any active shifts to DB before exit
        await self._flush_active_shifts()
        logger.info("Employee Analytics Worker stopped")

    async def register_pos_transaction(self, camera_id: str, employee_id: str, ticket_id: str, amount: float, timestamp: float) -> None:
        """Register a POS receipt to match with customer interactions."""
        async with self.lock:
            self.pos_transactions.append({
                "timestamp": timestamp,
                "datetime": datetime.fromtimestamp(timestamp),
                "employee_id": employee_id,
                "camera_id": camera_id,
                "ticket_id": ticket_id,
                "amount": amount
            })
            
            # Clean up old transactions (keep last 10 minutes)
            cutoff = datetime.now() - timedelta(minutes=10)
            self.pos_transactions = [t for t in self.pos_transactions if t["datetime"] > cutoff]
            logger.info("Registered POS transaction for conversion matching", employee_id=employee_id, ticket_id=ticket_id)

    async def _load_camera_calibrations(self) -> None:
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(Camera))
            cameras = res.scalars().all()
            for cam in cameras:
                cfg = cam.config_json or {}
                homography_cfg = cfg.get("homography", {})
                if homography_cfg and homography_cfg.get("enabled", False):
                    # Load calculated matrix H directly if it exists, otherwise calibrate
                    matrix_H = homography_cfg.get("matrix_H")
                    if matrix_H:
                        calibrator = HomographyCalibrator.from_dict({"H": matrix_H})
                    else:
                        calibrator = HomographyCalibrator(
                            pixel_points=homography_cfg.get("pixel_points", []),
                            world_points=homography_cfg.get("world_points", [])
                        )
                    self.calibrators[cam.id] = calibrator

    async def process_zone_entry(self, data: Dict[str, Any]) -> None:
        """Handle zone entry to trigger shift logic."""
        camera_id = data.get("camera_id")
        track_id = data.get("track_id")
        zone_name = data.get("zone_name")
        ts = data.get("timestamp", time.time())
        ts_datetime = datetime.fromtimestamp(ts)
        
        if zone_name != "worker_cabin":
            return
            
        async with self.lock:
            employee_id = self._resolve_employee_id(camera_id, track_id)
            
            # Retrieve or create active shift
            if employee_id not in self.active_shifts:
                # Check DB for existing open shift today
                shift_data = await self._get_or_create_shift_db(camera_id, employee_id, ts_datetime)
                self.active_shifts[employee_id] = shift_data
            else:
                shift = self.active_shifts[employee_id]
                # If they were marked on a break (out of cabin), resume
                if not shift["in_cabin"]:
                    exit_time = shift["cabin_exit_time"]
                    if exit_time:
                        absence = (ts_datetime - exit_time).total_seconds()
                        if absence >= 300.0:  # 5 minutes break threshold
                            shift["total_break_seconds"] += absence
                    shift["in_cabin"] = True
                    shift["cabin_exit_time"] = None
                    shift["last_seen_tick"] = ts_datetime
                shift["last_seen"] = ts_datetime
                await self._save_shift_to_db(shift)

    async def process_detection(self, data: Dict[str, Any]) -> None:
        """Process real-time coordinates of tracks for shift presence, idle time and proximity interactions."""
        if not self.running:
            return
            
        camera_id = data.get("camera_id")
        ts = data.get("timestamp", time.time())
        ts_datetime = datetime.fromtimestamp(ts)
        tracked_objects = data.get("tracked_objects", [])
        
        async with self.lock:
            # 1. Map current tracks
            employees: Dict[str, Dict[str, Any]] = {}  # employee_id -> object dict
            customers: List[Dict[str, Any]] = []
            
            for obj in tracked_objects:
                track_id = obj.get("track_id")
                role = obj.get("role")
                zone_name = obj.get("zone_name")
                
                # Check if it represents an employee
                employee_id = None
                if role == "worker" or zone_name == "worker_cabin":
                    employee_id = self._resolve_employee_id(camera_id, track_id)
                else:
                    # Check if this track_id is actively mapped to a shift
                    for emp, shift in self.active_shifts.items():
                        if shift["track_id"] == track_id and shift["camera_id"] == camera_id:
                            employee_id = emp
                            break
                            
                if employee_id:
                    employees[employee_id] = obj
                elif obj.get("class_name") == "person":
                    customers.append(obj)
            
            # 2. Update shifts state
            for employee_id, obj in employees.items():
                track_id = obj.get("track_id")
                zone_name = obj.get("zone_name")
                
                # Initialize shift if missing
                if employee_id not in self.active_shifts:
                    shift_data = await self._get_or_create_shift_db(camera_id, employee_id, ts_datetime)
                    shift_data["track_id"] = track_id
                    self.active_shifts[employee_id] = shift_data
                
                shift = self.active_shifts[employee_id]
                shift["track_id"] = track_id  # Update track_id in case it changed due to tracking reset
                shift["last_seen"] = ts_datetime
                
                # Presence update
                if shift["in_cabin"]:
                    elapsed = (ts_datetime - shift["last_seen_tick"]).total_seconds()
                    if 0 < elapsed < 10:  # Bound sanity check
                        shift["total_presence_seconds"] += elapsed
                else:
                    # Entered cabin again
                    shift["in_cabin"] = True
                    shift["cabin_exit_time"] = None
                    
                shift["last_seen_tick"] = ts_datetime
                
                # Calculate Idle time: present but no customer nearby
                has_customer_nearby = False
                calibrator = self.calibrators.get(camera_id)
                emp_box = obj.get("box", {})
                emp_x = (emp_box.get("x1", 0.0) + emp_box.get("x2", 0.0)) / 2.0
                emp_y = emp_box.get("y2", 0.0)
                
                if calibrator:
                    emp_world = calibrator.pixel_to_world(emp_x, emp_y)
                else:
                    emp_world = (emp_x * 0.02, emp_y * 0.02)
                    
                for cust in customers:
                    cust_box = cust.get("box", {})
                    cx = (cust_box.get("x1", 0.0) + cust_box.get("x2", 0.0)) / 2.0
                    cy = cust_box.get("y2", 0.0)
                    
                    if calibrator:
                        cust_world = calibrator.pixel_to_world(cx, cy)
                    else:
                        cust_world = (cx * 0.02, cy * 0.02)
                        
                    dist = self._distance(emp_world, cust_world)
                    if dist < 1.5:  # Customer within 1.5m
                        has_customer_nearby = True
                        break
                        
                if not has_customer_nearby and shift["in_cabin"]:
                    elapsed = (ts_datetime - shift.get("last_idle_tick", ts_datetime)).total_seconds()
                    if 0 < elapsed < 10:
                        shift["total_idle_seconds"] += elapsed
                shift["last_idle_tick"] = ts_datetime
                
                # Save periodically or every tick
                await self._save_shift_to_db(shift)
                
            # 3. Break Check: If employee was in cabin but now not detected there
            for employee_id, shift in list(self.active_shifts.items()):
                if shift["camera_id"] == camera_id:
                    # If this employee is not in current frame detections list
                    if employee_id not in employees:
                        if shift["in_cabin"]:
                            shift["in_cabin"] = False
                            shift["cabin_exit_time"] = ts_datetime
                            await self._save_shift_to_db(shift)
                            
            # 4. Proximity Interactions checking
            for employee_id, obj in employees.items():
                emp_box = obj.get("box", {})
                emp_x = (emp_box.get("x1", 0.0) + emp_box.get("x2", 0.0)) / 2.0
                emp_y = emp_box.get("y2", 0.0)
                calibrator = self.calibrators.get(camera_id)
                
                if calibrator:
                    emp_world = calibrator.pixel_to_world(emp_x, emp_y)
                else:
                    emp_world = (emp_x * 0.02, emp_y * 0.02)
                    
                for cust in customers:
                    cust_track_id = cust.get("track_id")
                    cust_box = cust.get("box", {})
                    cx = (cust_box.get("x1", 0.0) + cust_box.get("x2", 0.0)) / 2.0
                    cy = cust_box.get("y2", 0.0)
                    
                    if calibrator:
                        cust_world = calibrator.pixel_to_world(cx, cy)
                    else:
                        cust_world = (cx * 0.02, cy * 0.02)
                        
                    dist = self._distance(emp_world, cust_world)
                    key = (employee_id, cust_track_id)
                    
                    if dist < 1.2:
                        # Inside interaction range
                        if key not in self.active_interactions:
                            self.active_interactions[key] = {
                                "start_time": ts_datetime,
                                "last_seen": ts_datetime,
                                "camera_id": camera_id
                            }
                        else:
                            self.active_interactions[key]["last_seen"] = ts_datetime
                    else:
                        # Outside interaction range, finish if active
                        await self._finish_interaction_if_active(key, ts_datetime)
            
            # 5. Clean up missing active interactions
            active_customer_ids = {c.get("track_id") for c in customers}
            for key in list(self.active_interactions.keys()):
                emp_id, cust_tid = key
                if self.active_interactions[key]["camera_id"] == camera_id:
                    # If customer disappeared, complete interaction
                    if cust_tid not in active_customer_ids:
                        await self._finish_interaction_if_active(key, ts_datetime)

    async def _finish_interaction_if_active(self, key: Tuple[str, int], current_time: datetime) -> None:
        interaction = self.active_interactions.get(key)
        if not interaction:
            return
            
        dur = (interaction["last_seen"] - interaction["start_time"]).total_seconds()
        if dur >= 10.0:  # Must last at least 10s to count
            employee_id, customer_track_id = key
            
            # Match with POS Transactions
            matched_ticket_id = None
            for txn in self.pos_transactions:
                if txn["employee_id"] == employee_id and txn["camera_id"] == interaction["camera_id"]:
                    # Time window matching: within 2 minutes of interaction end
                    if abs((txn["datetime"] - interaction["last_seen"]).total_seconds()) <= 120.0:
                        matched_ticket_id = txn["ticket_id"]
                        break
            
            # Persist to database
            async with AsyncSessionLocal() as db:
                db_interaction = StaffInteraction(
                    camera_id=interaction["camera_id"],
                    employee_id=employee_id,
                    customer_track_id=customer_track_id,
                    start_time=interaction["start_time"],
                    end_time=interaction["last_seen"],
                    duration_seconds=dur,
                    pos_ticket_id=matched_ticket_id
                )
                db.add(db_interaction)
                await db.commit()
                logger.info("Saved customer-employee interaction", employee_id=employee_id, duration=dur, pos_linked=matched_ticket_id)
                
        self.active_interactions.pop(key, None)

    async def _cleanup_loop(self) -> None:
        """Loop to clean up stale active shifts and interactions that disappeared from tracking."""
        while self.running:
            try:
                await asyncio.sleep(10)
                async with self.lock:
                    now = datetime.now()
                    
                    # 0. Reload camera employee mappings from DB
                    await self._load_camera_employee_mappings()
                    
                    # 1. Clean up stale interactions (no updates for 30s)
                    for key, interaction in list(self.active_interactions.items()):
                        if (now - interaction["last_seen"]).total_seconds() > 30.0:
                            await self._finish_interaction_if_active(key, now)
                            
                    # 2. Clean up stale shifts (no detections/updates for 30 minutes)
                    for employee_id, shift in list(self.active_shifts.items()):
                        if (now - shift["last_seen"]).total_seconds() > 1800.0:
                            # Close the shift in the active memory list
                            await self._save_shift_to_db(shift)
                            self.active_shifts.pop(employee_id, None)

                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in employee analytics cleanup loop", error=str(e))

    async def _flush_active_shifts(self) -> None:
        """Flush and save all active shifts state on stop."""
        async with self.lock:
            for shift in self.active_shifts.values():
                await self._save_shift_to_db(shift)

    async def _get_or_create_shift_db(self, camera_id: str, employee_id: str, ts: datetime) -> Dict[str, Any]:
        """Fetch open shift for today, or create a new shift schema."""
        date_start = ts.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        
        async with AsyncSessionLocal() as db:
            q = select(StaffShift).where(
                and_(
                    StaffShift.employee_id == employee_id,
                    StaffShift.camera_id == camera_id,
                    StaffShift.first_seen >= date_start,
                    StaffShift.first_seen < date_end
                )
            ).order_by(StaffShift.first_seen.desc())
            
            res = await db.execute(q)
            db_shift = res.scalar_one_or_none()
            
            if db_shift:
                return {
                    "id": db_shift.id,
                    "camera_id": db_shift.camera_id,
                    "employee_id": db_shift.employee_id,
                    "track_id": 0,
                    "first_seen": db_shift.first_seen,
                    "last_seen": db_shift.last_seen,
                    "last_seen_tick": ts,
                    "total_presence_seconds": db_shift.total_presence_seconds,
                    "total_break_seconds": db_shift.total_break_seconds,
                    "total_idle_seconds": db_shift.total_idle_seconds,
                    "in_cabin": True,
                    "cabin_exit_time": None
                }
            else:
                # Create shift in DB first
                db_shift = StaffShift(
                    employee_id=employee_id,
                    camera_id=camera_id,
                    workstation_zone="worker_cabin",
                    first_seen=ts,
                    last_seen=ts,
                    total_presence_seconds=0.0,
                    total_break_seconds=0.0,
                    total_idle_seconds=0.0
                )
                db.add(db_shift)
                await db.commit()
                
                return {
                    "id": db_shift.id,
                    "camera_id": camera_id,
                    "employee_id": employee_id,
                    "track_id": 0,
                    "first_seen": ts,
                    "last_seen": ts,
                    "last_seen_tick": ts,
                    "total_presence_seconds": 0.0,
                    "total_break_seconds": 0.0,
                    "total_idle_seconds": 0.0,
                    "in_cabin": True,
                    "cabin_exit_time": None
                }

    async def _save_shift_to_db(self, shift: Dict[str, Any]) -> None:
        """Sync the active shift dictionary back to SQLite."""
        async with AsyncSessionLocal() as db:
            q = select(StaffShift).where(StaffShift.id == shift["id"])
            res = await db.execute(q)
            db_shift = res.scalar_one_or_none()
            if db_shift:
                db_shift.last_seen = shift["last_seen"]
                db_shift.total_presence_seconds = shift["total_presence_seconds"]
                db_shift.total_break_seconds = shift["total_break_seconds"]
                db_shift.total_idle_seconds = shift["total_idle_seconds"]
                await db.commit()

    async def _load_camera_employee_mappings(self) -> None:
        """Fetch custom employee assignments from camera database configurations."""
        try:
            async with AsyncSessionLocal() as db:
                res = await db.execute(select(Camera))
                cameras = res.scalars().all()
                for cam in cameras:
                    cfg = cam.config_json or {}
                    zones = cfg.get("zones", [])
                    for zone in zones:
                        if zone.get("name") == "worker_cabin":
                            emp_id = zone.get("employee_id")
                            emp_name = zone.get("employee_name")
                            if emp_id:
                                self.camera_employee_cache[cam.id] = {
                                    "employee_id": emp_id,
                                    "employee_name": emp_name
                                }
                                break
        except Exception as ex:
            logger.error("Failed to load camera employee mappings", error=str(ex))

    def _resolve_employee_id(self, camera_id: str, track_id: int) -> str:
        """Resolve employee ID mapping from custom camera zones, static staff assignments, or defaults."""
        cached = self.camera_employee_cache.get(camera_id)
        if cached and cached.get("employee_id"):
            return cached["employee_id"]

        assignments = getattr(self.settings, "staff_assignments", [])
        for a in assignments:
            if getattr(a, "camera_id", None) == camera_id:
                return getattr(a, "employee_id", f"staff_{camera_id}_{track_id}")
        return f"staff_{camera_id}_{track_id}"

    def _distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)**0.5

