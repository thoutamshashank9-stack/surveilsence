import time
import asyncio
from typing import Dict, List, Any, Tuple
import numpy as np
import onnxruntime as ort
from app.core.logging import get_logger

logger = get_logger(__name__)

class DynamicFrameBatcher:
    """
    Dynamic frame batching manager to consolidate frames from multiple camera feeds
    into a single synchronized batch execution. 
    
    This is highly optimized for DirectML, avoiding concurrent session.run() 
    crashes on the Radeon iGPU.
    """
    def __init__(self, session: ort.InferenceSession, max_batch_size: int = 4, max_wait_ms: float = 10.0):
        self.session = session
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms / 1000.0  # Convert to seconds
        self.queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self.batch_task: Optional[asyncio.Task] = None

    def start(self):
        if not self.running:
            self.running = True
            self.batch_task = asyncio.create_task(self._batching_loop())
            logger.info("DynamicFrameBatcher started", max_batch_size=self.max_batch_size, max_wait_s=self.max_wait_ms)

    async def stop(self):
        self.running = False
        if self.batch_task:
            self.batch_task.cancel()
            try:
                await self.batch_task
            except asyncio.CancelledError:
                pass
            logger.info("DynamicFrameBatcher stopped")

    async def submit_frame(self, frame_tensor: np.ndarray) -> asyncio.Future:
        """
        Submit a preprocessed frame tensor (e.g. [1, 3, 640, 640]) to the batcher.
        Returns a Future that will resolve to the inference results.
        """
        future = asyncio.get_event_loop().create_future()
        await self.queue.put((frame_tensor, future))
        return future

    async def _batching_loop(self):
        while self.running:
            try:
                # Wait for the first item
                item = await self.queue.get()
                batch_items = [item]
                start_time = time.time()

                # Collect more items until max_batch_size or max_wait_ms is reached
                while len(batch_items) < self.max_batch_size:
                    time_left = self.max_wait_ms - (time.time() - start_time)
                    if time_left <= 0:
                        break
                    
                    try:
                        # Wait for next item with timeout
                        next_item = await asyncio.wait_for(self.queue.get(), timeout=time_left)
                        batch_items.append(next_item)
                    except asyncio.TimeoutError:
                        break

                # Prepare the batch inputs
                tensors = [item[0] for item in batch_items]
                futures = [item[1] for item in batch_items]

                # Concatenate along batch dimension (axis 0)
                # Ensure each input tensor is [1, C, H, W] -> concatenated to [N, C, H, W]
                batched_tensor = np.concatenate(tensors, axis=0)

                # Execute inference
                input_name = self.session.get_inputs()[0].name
                output_names = [o.name for o in self.session.get_outputs()]
                
                # Executed synchronously inside the worker thread
                loop = asyncio.get_event_loop()
                outputs = await loop.run_in_executor(
                    None, 
                    self.session.run, 
                    output_names, 
                    {input_name: batched_tensor}
                )

                # Fan results back to individual futures
                # For output tensors, we slice them along axis 0
                for idx, future in enumerate(futures):
                    if not future.cancelled():
                        # Extract outputs for item idx in the batch
                        item_outputs = []
                        for out in outputs:
                            item_outputs.append(np.expand_dims(out[idx], axis=0))
                        future.set_result(item_outputs)

                # Mark queue items as done
                for _ in range(len(batch_items)):
                    self.queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in dynamic frame batcher execution", error=str(e))
                # Fail all pending futures in current batch
                for item in batch_items:
                    if not item[1].done() and not item[1].cancelled():
                        item[1].set_exception(e)
                await asyncio.sleep(0.01)
