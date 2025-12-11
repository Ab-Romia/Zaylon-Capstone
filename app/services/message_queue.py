"""
Message Queue Service
Phase 5: Handles message queuing, debouncing, and burst aggregation.

Features:
- Message queuing with priority
- Debouncing rapid messages (typing indicators)
- Burst message aggregation
- Duplicate detection
- Queue management for high traffic
"""
import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class QueuedMessage:
    """Represents a queued message."""

    message_id: str
    customer_id: str
    content: str
    channel: str
    timestamp: float
    priority: int = 0  # 0=normal, 1=high, 2=urgent
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Debouncing
    is_typing: bool = False  # Typing indicator
    debounce_until: Optional[float] = None  # Wait until this timestamp

    # Aggregation
    burst_group_id: Optional[str] = None  # Group ID for burst messages
    aggregated_messages: List[str] = field(default_factory=list)


@dataclass
class ProcessingResult:
    """Result of message processing."""

    success: bool
    message_id: str
    customer_id: str
    response: Optional[str] = None
    processing_time: float = 0.0
    was_aggregated: bool = False
    aggregated_count: int = 0
    error: Optional[str] = None


class MessageQueueService:
    """
    Service for managing message queues with debouncing and aggregation.

    Features:
    - Debouncing: Wait for user to finish typing
    - Burst aggregation: Combine rapid messages into one context
    - Duplicate detection: Prevent processing same message twice
    - Priority queuing: Urgent messages first
    - High traffic management: Queue when overwhelmed
    """

    def __init__(
        self,
        debounce_window: float = 2.0,  # Wait 2s after last message
        burst_window: float = 5.0,  # Messages within 5s are a burst
        max_queue_size: int = 1000,
        max_concurrent_processing: int = 10
    ):
        """
        Initialize message queue service.

        Args:
            debounce_window: Seconds to wait after last message before processing
            burst_window: Seconds to consider messages as part of same burst
            max_queue_size: Maximum queue size before rejecting messages
            max_concurrent_processing: Max messages processing simultaneously
        """
        self.debounce_window = debounce_window
        self.burst_window = burst_window
        self.max_queue_size = max_queue_size
        self.max_concurrent_processing = max_concurrent_processing

        # Message queues (per customer)
        self.queues: Dict[str, List[QueuedMessage]] = defaultdict(list)

        # Currently processing
        self.processing: Dict[str, QueuedMessage] = {}

        # Duplicate detection (content hash → timestamp)
        self.processed_hashes: Dict[str, float] = {}
        self.hash_ttl = 300.0  # 5 minutes

        # Burst tracking (customer_id → last message time)
        self.last_message_time: Dict[str, float] = {}
        self.burst_groups: Dict[str, str] = {}  # customer_id → burst_group_id

        # Locks for thread safety
        self.locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

        # Statistics
        self.stats = {
            "total_queued": 0,
            "total_processed": 0,
            "total_debounced": 0,
            "total_aggregated": 0,
            "total_duplicates": 0,
            "total_rejected": 0
        }

    async def enqueue_message(
        self,
        customer_id: str,
        content: str,
        channel: str,
        message_id: Optional[str] = None,
        priority: int = 0,
        is_typing: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Enqueue a message for processing.

        Args:
            customer_id: Customer identifier
            content: Message content
            channel: Communication channel (instagram, whatsapp, web)
            message_id: Optional message ID (auto-generated if None)
            priority: Priority level (0=normal, 1=high, 2=urgent)
            is_typing: Whether this is a typing indicator
            metadata: Additional metadata

        Returns:
            Tuple of (success, message/error)
        """
        async with self.locks[customer_id]:
            # Generate message ID if not provided
            if not message_id:
                message_id = self._generate_message_id(customer_id, content)

            # Check for duplicates
            content_hash = self._hash_content(content)
            if self._is_duplicate(content_hash):
                self.stats["total_duplicates"] += 1
                logger.info(f"Duplicate message detected for {customer_id}: {content[:50]}")
                return False, "Duplicate message (already processed)"

            # Check queue size
            total_queued = sum(len(q) for q in self.queues.values())
            if total_queued >= self.max_queue_size:
                self.stats["total_rejected"] += 1
                logger.warning(f"Queue full ({total_queued}/{self.max_queue_size}), rejecting message")
                return False, "Queue full, please try again"

            # Check if this is part of a burst
            current_time = time.time()
            last_time = self.last_message_time.get(customer_id, 0)
            is_burst = (current_time - last_time) < self.burst_window

            # Generate or reuse burst group ID
            if is_burst and customer_id in self.burst_groups:
                burst_group_id = self.burst_groups[customer_id]
            else:
                burst_group_id = f"{customer_id}_{int(current_time)}"
                self.burst_groups[customer_id] = burst_group_id

            # Update last message time
            self.last_message_time[customer_id] = current_time

            # Create queued message
            queued_message = QueuedMessage(
                message_id=message_id,
                customer_id=customer_id,
                content=content,
                channel=channel,
                timestamp=current_time,
                priority=priority,
                metadata=metadata or {},
                is_typing=is_typing,
                debounce_until=current_time + self.debounce_window if not is_typing else None,
                burst_group_id=burst_group_id
            )

            # Add to queue
            self.queues[customer_id].append(queued_message)
            self.stats["total_queued"] += 1

            # Sort by priority (higher priority first)
            self.queues[customer_id].sort(key=lambda m: (-m.priority, m.timestamp))

            logger.info(
                f"Enqueued message for {customer_id} "
                f"(priority: {priority}, burst: {is_burst}, typing: {is_typing})"
            )

            return True, message_id

    async def process_queue(
        self,
        customer_id: str,
        processor_func
    ) -> Optional[ProcessingResult]:
        """
        Process messages from queue for a customer.

        Args:
            customer_id: Customer identifier
            processor_func: Async function to process message (takes QueuedMessage, returns response)

        Returns:
            ProcessingResult or None if no messages ready
        """
        async with self.locks[customer_id]:
            # Check if already processing for this customer
            if customer_id in self.processing:
                logger.debug(f"Already processing message for {customer_id}")
                return None

            # Get customer's queue
            queue = self.queues.get(customer_id, [])
            if not queue:
                return None

            # Find next message to process (respecting debounce)
            current_time = time.time()
            ready_messages = [
                msg for msg in queue
                if not msg.is_typing and (
                    msg.debounce_until is None or
                    current_time >= msg.debounce_until
                )
            ]

            if not ready_messages:
                # Still debouncing
                return None

            # Check for burst aggregation
            burst_group = ready_messages[0].burst_group_id
            burst_messages = [
                msg for msg in ready_messages
                if msg.burst_group_id == burst_group
            ]

            if len(burst_messages) > 1:
                # Aggregate burst messages
                primary_message = burst_messages[0]
                aggregated_content = self._aggregate_messages(burst_messages)
                primary_message.content = aggregated_content
                primary_message.aggregated_messages = [m.content for m in burst_messages[1:]]

                # Remove aggregated messages from queue
                for msg in burst_messages:
                    queue.remove(msg)

                message_to_process = primary_message
                self.stats["total_aggregated"] += len(burst_messages) - 1

                logger.info(
                    f"Aggregated {len(burst_messages)} messages for {customer_id} "
                    f"into one request"
                )
            else:
                # Single message
                message_to_process = ready_messages[0]
                queue.remove(message_to_process)

            # Mark as processing
            self.processing[customer_id] = message_to_process

        # Process message (outside lock to avoid blocking queue)
        start_time = time.time()
        try:
            response = await processor_func(message_to_process)
            processing_time = time.time() - start_time

            # Mark content as processed
            content_hash = self._hash_content(message_to_process.content)
            self.processed_hashes[content_hash] = time.time()

            self.stats["total_processed"] += 1

            result = ProcessingResult(
                success=True,
                message_id=message_to_process.message_id,
                customer_id=customer_id,
                response=response,
                processing_time=processing_time,
                was_aggregated=len(message_to_process.aggregated_messages) > 0,
                aggregated_count=len(message_to_process.aggregated_messages)
            )

            logger.info(
                f"Processed message {message_to_process.message_id} for {customer_id} "
                f"in {processing_time:.2f}s"
            )

        except Exception as e:
            logger.error(f"Error processing message for {customer_id}: {e}", exc_info=True)
            result = ProcessingResult(
                success=False,
                message_id=message_to_process.message_id,
                customer_id=customer_id,
                error=str(e)
            )

        finally:
            # Remove from processing
            async with self.locks[customer_id]:
                if customer_id in self.processing:
                    del self.processing[customer_id]

        return result

    def _aggregate_messages(self, messages: List[QueuedMessage]) -> str:
        """
        Aggregate multiple messages into one context.

        Args:
            messages: List of messages to aggregate

        Returns:
            Aggregated content string
        """
        if len(messages) == 1:
            return messages[0].content

        # Combine messages with indicators
        parts = []
        for i, msg in enumerate(messages, 1):
            parts.append(f"[Message {i}]: {msg.content}")

        aggregated = "\n".join(parts)

        # Add aggregation notice
        header = f"[User sent {len(messages)} messages in quick succession. Context below:]\n"

        return header + aggregated

    def _hash_content(self, content: str) -> str:
        """Generate hash for duplicate detection."""
        normalized = content.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()

    def _is_duplicate(self, content_hash: str) -> bool:
        """Check if content hash was recently processed."""
        if content_hash not in self.processed_hashes:
            return False

        # Check if hash has expired
        processed_time = self.processed_hashes[content_hash]
        if time.time() - processed_time > self.hash_ttl:
            # Expired, remove from cache
            del self.processed_hashes[content_hash]
            return False

        return True

    def _generate_message_id(self, customer_id: str, content: str) -> str:
        """Generate unique message ID."""
        timestamp = int(time.time() * 1000)
        content_preview = content[:20].replace(" ", "_")
        return f"{customer_id}_{timestamp}_{content_preview}"

    async def cleanup_expired(self):
        """Clean up expired hashes and old burst groups."""
        current_time = time.time()

        # Clean processed hashes
        expired_hashes = [
            h for h, t in self.processed_hashes.items()
            if current_time - t > self.hash_ttl
        ]
        for h in expired_hashes:
            del self.processed_hashes[h]

        # Clean old burst groups (older than burst window)
        expired_bursts = [
            cid for cid, t in self.last_message_time.items()
            if current_time - t > self.burst_window
        ]
        for cid in expired_bursts:
            if cid in self.burst_groups:
                del self.burst_groups[cid]
            del self.last_message_time[cid]

        if expired_hashes or expired_bursts:
            logger.debug(
                f"Cleaned up {len(expired_hashes)} hashes and "
                f"{len(expired_bursts)} burst groups"
            )

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        total_queued = sum(len(q) for q in self.queues.values())
        total_processing = len(self.processing)

        return {
            **self.stats,
            "queues": {
                "total_queued": total_queued,
                "total_processing": total_processing,
                "customers_in_queue": len(self.queues),
                "queue_by_customer": {
                    cid: len(q) for cid, q in self.queues.items() if q
                }
            },
            "cache": {
                "processed_hashes": len(self.processed_hashes),
                "active_burst_groups": len(self.burst_groups)
            }
        }

    def get_customer_queue_status(self, customer_id: str) -> Dict[str, Any]:
        """Get queue status for specific customer."""
        queue = self.queues.get(customer_id, [])
        is_processing = customer_id in self.processing

        return {
            "customer_id": customer_id,
            "queue_size": len(queue),
            "is_processing": is_processing,
            "messages": [
                {
                    "message_id": msg.message_id,
                    "timestamp": msg.timestamp,
                    "priority": msg.priority,
                    "is_typing": msg.is_typing,
                    "debounce_until": msg.debounce_until,
                    "burst_group": msg.burst_group_id
                }
                for msg in queue
            ]
        }


# Singleton instance
_message_queue_service: Optional[MessageQueueService] = None


def get_message_queue_service(
    debounce_window: float = 2.0,
    burst_window: float = 5.0
) -> MessageQueueService:
    """Get or create the global message queue service."""
    global _message_queue_service
    if _message_queue_service is None:
        _message_queue_service = MessageQueueService(
            debounce_window=debounce_window,
            burst_window=burst_window
        )
    return _message_queue_service
