"""
Queue Middleware
Phase 5: Middleware for integrating message queue into API endpoints.

Usage:
    From synchronous endpoint, enqueue message and return immediately.
    Background worker processes queue asynchronously.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.services.message_queue import get_message_queue_service

logger = logging.getLogger(__name__)


class QueueMiddleware:
    """
    Middleware for message queuing in API endpoints.

    Features:
    - Enqueue messages instead of immediate processing
    - Return quickly to client
    - Background worker processes queue
    """

    def __init__(
        self,
        enable_queue: bool = True,
        debounce_window: float = 2.0
    ):
        """
        Initialize queue middleware.

        Args:
            enable_queue: Whether to enable queuing (False = immediate processing)
            debounce_window: Debounce window in seconds
        """
        self.enable_queue = enable_queue
        self.queue_service = get_message_queue_service(
            debounce_window=debounce_window
        )

    async def enqueue_message(
        self,
        customer_id: str,
        message: str,
        channel: str,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """
        Enqueue a message for processing.

        Args:
            customer_id: Customer identifier
            message: Message content
            channel: Channel (instagram, whatsapp, web)
            priority: Priority level (0=normal, 1=high, 2=urgent)
            metadata: Additional metadata

        Returns:
            JSON response with queue status
        """
        if not self.enable_queue:
            # Queuing disabled, signal immediate processing needed
            return JSONResponse(
                status_code=200,
                content={
                    "status": "processing",
                    "message": "Processing immediately (queue disabled)",
                    "queued": False
                }
            )

        # Enqueue message
        success, result = await self.queue_service.enqueue_message(
            customer_id=customer_id,
            content=message,
            channel=channel,
            priority=priority,
            metadata=metadata
        )

        if success:
            # Successfully queued
            return JSONResponse(
                status_code=202,  # Accepted
                content={
                    "status": "queued",
                    "message_id": result,
                    "message": "Message queued for processing",
                    "queued": True,
                    "estimated_processing_time": f"{self.queue_service.debounce_window}s"
                }
            )
        else:
            # Failed to queue (duplicate or queue full)
            return JSONResponse(
                status_code=429 if "full" in result else 200,
                content={
                    "status": "rejected" if "full" in result else "duplicate",
                    "message": result,
                    "queued": False
                }
            )

    def detect_urgent_message(self, message: str) -> bool:
        """
        Detect if message is urgent and should have higher priority.

        Args:
            message: Message content

        Returns:
            True if urgent
        """
        urgent_indicators = [
            "urgent", "asap", "emergency", "immediately",
            "!!!",  # Multiple exclamation marks
            "عاجل", "سريع", "فوري",  # Arabic
            "urgente", "rápido"  # Spanish
        ]

        message_lower = message.lower()
        return any(indicator in message_lower for indicator in urgent_indicators)

    def get_queue_status(self, customer_id: str) -> Dict[str, Any]:
        """
        Get queue status for a customer.

        Args:
            customer_id: Customer identifier

        Returns:
            Queue status dictionary
        """
        return self.queue_service.get_customer_queue_status(customer_id)


# Singleton instance
_queue_middleware: Optional[QueueMiddleware] = None


def get_queue_middleware(enable_queue: bool = True) -> QueueMiddleware:
    """Get or create the global queue middleware."""
    global _queue_middleware
    if _queue_middleware is None:
        _queue_middleware = QueueMiddleware(enable_queue=enable_queue)
    return _queue_middleware
