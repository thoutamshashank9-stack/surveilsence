import asyncio
from typing import Dict, List, Callable, Any, Awaitable, Optional
from app.models.enums import EventType
from app.core.logging import get_logger

logger = get_logger(__name__)

class EventBus:
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable[[Any], Awaitable[None]]]] = {
            t: [] for t in EventType
        }
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._running: bool = False

    async def publish(self, event_type: EventType, data: Any) -> None:
        if self._running:
            await self._queue.put((event_type, data))

    def subscribe(self, event_type: EventType, handler: Callable[[Any], Awaitable[None]]) -> None:
        if event_type in self._subscribers:
            self._subscribers[event_type].append(handler)
        else:
            self._subscribers[event_type] = [handler]

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        logger.info("Event bus started")

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Event bus stopped")

    async def _process_queue(self) -> None:
        while self._running:
            try:
                event_type, data = await self._queue.get()
                handlers = self._subscribers.get(event_type, [])
                if handlers:
                    # Run handlers concurrently
                    await asyncio.gather(
                        *[h(data) for h in handlers],
                        return_exceptions=True
                    )
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error processing event", error=str(e))
                await asyncio.sleep(0.1)
