"""Background task manager for non-blocking operations like analytics logging."""

import asyncio
import logging
from typing import Any, Callable, Coroutine
from collections import deque

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """
    Manages background tasks for non-blocking operations.
    Used primarily for analytics logging to avoid blocking the main request path.
    """

    def __init__(self, max_queue_size: int = 1000):
        self._queue: deque = deque(maxlen=max_queue_size)
        self._running = False
        self._task = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Start the background task processor."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._process_queue())
        logger.info("Background task manager started")

    async def stop(self):
        """Stop the background task processor gracefully."""
        self._running = False
        if self._task:
            # Process remaining tasks
            while self._queue:
                await self._process_single_task()
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Background task manager stopped")

    def add_task(self, coro: Coroutine):
        """Add a coroutine to the background queue."""
        if len(self._queue) >= self._queue.maxlen:
            logger.warning("Background queue full, dropping oldest task")
        self._queue.append(coro)

    async def _process_queue(self):
        """Process tasks from the queue."""
        while self._running:
            await self._process_single_task()
            await asyncio.sleep(0.01)  # Small delay to prevent CPU spinning

    async def _process_single_task(self):
        """Process a single task from the queue."""
        if not self._queue:
            return

        async with self._lock:
            if not self._queue:
                return
            coro = self._queue.popleft()

        try:
            await coro
        except Exception as e:
            logger.error(f"Background task failed: {e}", exc_info=True)


# Global instance
background_tasks = BackgroundTaskManager()
