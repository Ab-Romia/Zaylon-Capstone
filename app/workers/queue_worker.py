"""
Queue Worker
Phase 5: Background worker for processing message queues.

Features:
- Continuous queue processing
- Periodic cleanup of expired data
- Graceful shutdown
- Health monitoring
"""
import asyncio
import logging
from typing import Optional, Callable
from datetime import datetime
import signal

from app.services.message_queue import get_message_queue_service, QueuedMessage

logger = logging.getLogger(__name__)


class QueueWorker:
    """
    Background worker for processing message queues.

    Features:
    - Polls queues for ready messages
    - Processes messages using provided processor function
    - Periodic cleanup of expired data
    - Graceful shutdown on signals
    - Health monitoring
    """

    def __init__(
        self,
        processor_func: Callable,
        poll_interval: float = 0.5,  # Poll every 500ms
        cleanup_interval: float = 60.0  # Cleanup every 60s
    ):
        """
        Initialize queue worker.

        Args:
            processor_func: Async function to process messages
            poll_interval: Seconds between queue polls
            cleanup_interval: Seconds between cleanup runs
        """
        self.processor_func = processor_func
        self.poll_interval = poll_interval
        self.cleanup_interval = cleanup_interval

        self.queue_service = get_message_queue_service()
        self.running = False
        self.tasks = []

        # Health metrics
        self.start_time = None
        self.last_poll_time = None
        self.last_cleanup_time = None
        self.processed_count = 0

    async def start(self):
        """Start the queue worker."""
        if self.running:
            logger.warning("Queue worker already running")
            return

        self.running = True
        self.start_time = datetime.utcnow()

        logger.info(
            f"Starting queue worker "
            f"(poll: {self.poll_interval}s, cleanup: {self.cleanup_interval}s)"
        )

        # Start background tasks
        self.tasks = [
            asyncio.create_task(self._poll_loop()),
            asyncio.create_task(self._cleanup_loop())
        ]

        # Setup signal handlers for graceful shutdown
        try:
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
        except NotImplementedError:
            # Windows doesn't support signal handlers in asyncio
            logger.warning("Signal handlers not supported on this platform")

        logger.info("Queue worker started successfully")

    async def stop(self):
        """Stop the queue worker gracefully."""
        if not self.running:
            return

        logger.info("Stopping queue worker...")
        self.running = False

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Wait for tasks to finish
        await asyncio.gather(*self.tasks, return_exceptions=True)

        logger.info(
            f"Queue worker stopped. "
            f"Processed {self.processed_count} messages total."
        )

    async def _poll_loop(self):
        """Continuously poll queues for ready messages."""
        logger.info("Poll loop started")

        while self.running:
            try:
                self.last_poll_time = datetime.utcnow()

                # Get all customer IDs with queued messages
                customer_ids = list(self.queue_service.queues.keys())

                if customer_ids:
                    # Process queues for each customer
                    tasks = [
                        self._process_customer_queue(customer_id)
                        for customer_id in customer_ids
                    ]
                    await asyncio.gather(*tasks, return_exceptions=True)

                # Wait before next poll
                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                logger.info("Poll loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in poll loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def _process_customer_queue(self, customer_id: str):
        """Process queue for a specific customer."""
        try:
            result = await self.queue_service.process_queue(
                customer_id=customer_id,
                processor_func=self.processor_func
            )

            if result:
                self.processed_count += 1

                if result.success:
                    logger.info(
                        f"Processed message for {customer_id} "
                        f"(time: {result.processing_time:.2f}s, "
                        f"aggregated: {result.aggregated_count})"
                    )
                else:
                    logger.error(
                        f"Failed to process message for {customer_id}: "
                        f"{result.error}"
                    )

        except Exception as e:
            logger.error(
                f"Error processing queue for {customer_id}: {e}",
                exc_info=True
            )

    async def _cleanup_loop(self):
        """Periodically cleanup expired data."""
        logger.info("Cleanup loop started")

        while self.running:
            try:
                await asyncio.sleep(self.cleanup_interval)

                self.last_cleanup_time = datetime.utcnow()

                # Run cleanup
                await self.queue_service.cleanup_expired()

                logger.debug("Cleanup completed")

            except asyncio.CancelledError:
                logger.info("Cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)

    def get_health_status(self) -> dict:
        """Get worker health status."""
        uptime = None
        if self.start_time:
            uptime = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            "running": self.running,
            "uptime_seconds": uptime,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_poll": self.last_poll_time.isoformat() if self.last_poll_time else None,
            "last_cleanup": self.last_cleanup_time.isoformat() if self.last_cleanup_time else None,
            "processed_count": self.processed_count,
            "queue_stats": self.queue_service.get_queue_stats()
        }


# Global worker instance
_queue_worker: Optional[QueueWorker] = None


def get_queue_worker(processor_func: Optional[Callable] = None) -> QueueWorker:
    """Get or create the global queue worker."""
    global _queue_worker
    if _queue_worker is None:
        if processor_func is None:
            raise ValueError("processor_func required for first initialization")
        _queue_worker = QueueWorker(processor_func=processor_func)
    return _queue_worker


async def start_queue_worker(processor_func: Callable):
    """Start the queue worker (convenience function)."""
    worker = get_queue_worker(processor_func)
    await worker.start()


async def stop_queue_worker():
    """Stop the queue worker (convenience function)."""
    global _queue_worker
    if _queue_worker:
        await _queue_worker.stop()
