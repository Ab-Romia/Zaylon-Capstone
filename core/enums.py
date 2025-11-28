"""Enums for type-safe values throughout the application."""

from enum import Enum


class EventType(str, Enum):
    """Analytics event types."""
    MESSAGE_RECEIVED = "message_received"
    INTENT_CLASSIFIED = "intent_classified"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    ORDER_CREATED = "order_created"
    ORDER_FAILED = "order_failed"
    PRODUCT_SEARCHED = "product_searched"
    CONTEXT_RETRIEVED = "context_retrieved"
    INTERACTION_COMPLETE = "interaction_complete"
    # Agentic system events
    AGENT_INVOKED = "agent_invoked"
    AGENT_ROUTED = "agent_routed"
    MEMORY_LOADED = "memory_loaded"
    MEMORY_SAVED = "memory_saved"


class OrderStatus(str, Enum):
    """Order status values."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Intent(str, Enum):
    """Customer message intents."""
    GREETING = "greeting"
    THANKS = "thanks"
    GOODBYE = "goodbye"
    PRICE_INQUIRY = "price_inquiry"
    ORDER_INTENT = "order_intent"
    AVAILABILITY_CHECK = "availability_check"
    VARIANT_INQUIRY = "variant_inquiry"
    ORDER_STATUS = "order_status"
    COMPLAINT = "complaint"
    GENERAL_INQUIRY = "general_inquiry"


class Channel(str, Enum):
    """Communication channels."""
    INSTAGRAM = "instagram"
    WHATSAPP = "whatsapp"


class Direction(str, Enum):
    """Message direction."""
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class SearchMethod(str, Enum):
    """RAG search methods."""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class Language(str, Enum):
    """Supported languages."""
    ARABIC = "ar"
    FRANCO_ARABIC = "franco"
    ENGLISH = "en"
