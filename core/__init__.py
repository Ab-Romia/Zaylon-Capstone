"""Core modules for the application."""

from .enums import EventType, OrderStatus, Intent, Channel, Direction
from .constants import (
    MESSAGE_TRUNCATE_LENGTH,
    CONTEXT_HISTORY_DISPLAY_LIMIT,
    CONTEXT_CACHE_TTL,
    MAX_CACHE_SIZE,
    AI_COST_PER_1K_INPUT,
    AI_COST_PER_1K_OUTPUT,
    PHONE_PATTERN,
    EMBEDDING_DIMENSION_OPENAI,
    EMBEDDING_DIMENSION_LOCAL,
)
from .background import BackgroundTaskManager, background_tasks

__all__ = [
    # Enums
    "EventType",
    "OrderStatus",
    "Intent",
    "Channel",
    "Direction",
    # Constants
    "MESSAGE_TRUNCATE_LENGTH",
    "CONTEXT_HISTORY_DISPLAY_LIMIT",
    "CONTEXT_CACHE_TTL",
    "MAX_CACHE_SIZE",
    "AI_COST_PER_1K_INPUT",
    "AI_COST_PER_1K_OUTPUT",
    "PHONE_PATTERN",
    "EMBEDDING_DIMENSION_OPENAI",
    "EMBEDDING_DIMENSION_LOCAL",
    # Background tasks
    "BackgroundTaskManager",
    "background_tasks",
]
