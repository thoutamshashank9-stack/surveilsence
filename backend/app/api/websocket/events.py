import asyncio
from typing import Dict, Any
from app.core.events import EventBus
from app.models.enums import EventType
from app.api.websocket.manager import ConnectionManager
from app.core.logging import get_logger

logger = get_logger(__name__)

class EventBroadcaster:
    def __init__(self, event_bus: EventBus, manager: ConnectionManager):
        self.event_bus = event_bus
        self.manager = manager
        self.running = False

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        
        # Subscribe to Event Bus events
        self.event_bus.subscribe(EventType.DETECTION, self.broadcast_detection)
        self.event_bus.subscribe(EventType.ALERT, self.broadcast_alert)
        self.event_bus.subscribe(EventType.ZONE_ENTRY, self.broadcast_zone_event)
        self.event_bus.subscribe(EventType.ZONE_EXIT, self.broadcast_zone_event)
        self.event_bus.subscribe(EventType.LINE_CROSS, self.broadcast_line_cross)
        
        logger.info("Event broadcaster listening to event bus")

    async def broadcast_detection(self, data: Dict[str, Any]) -> None:
        await self.manager.broadcast({
            "type": "detection",
            "timestamp": data.get("timestamp"),
            "camera_id": data.get("camera_id"),
            "data": data.get("tracked_objects", [])
        })

    async def broadcast_alert(self, data: Dict[str, Any]) -> None:
        await self.manager.broadcast({
            "type": "alert",
            "timestamp": data.get("timestamp"),
            "camera_id": data.get("camera_id"),
            "data": data
        })

    async def broadcast_zone_event(self, data: Dict[str, Any]) -> None:
        await self.manager.broadcast({
            "type": "zone_transition",
            "timestamp": data.get("timestamp"),
            "camera_id": data.get("camera_id"),
            "data": data
        })

    async def broadcast_line_cross(self, data: Dict[str, Any]) -> None:
        await self.manager.broadcast({
            "type": "line_cross",
            "timestamp": data.get("timestamp"),
            "camera_id": data.get("camera_id"),
            "data": data
        })
