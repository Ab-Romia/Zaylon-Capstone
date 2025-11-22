"""
Conversation context management service.
Handles conversation history storage, retrieval, and cross-channel linking.
OPTIMIZED: Added in-memory caching for frequent lookups.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, or_, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from database import Conversation, Customer
from models import (
    MessageInfo, CustomerMetadata, RetrieveContextResponse,
    StoreContextResponse, LinkChannelsResponse
)
from services.products import detect_language
import logging
import uuid
import time

logger = logging.getLogger(__name__)

# Simple in-memory cache for context (TTL: 30 seconds)
_context_cache: Dict[str, tuple] = {}  # {customer_id: (result, timestamp)}
CONTEXT_CACHE_TTL = 30  # seconds


def _get_cached_context(customer_id: str):
    """Get cached context if valid."""
    if customer_id in _context_cache:
        result, timestamp = _context_cache[customer_id]
        if time.time() - timestamp < CONTEXT_CACHE_TTL:
            return result
        else:
            del _context_cache[customer_id]
    return None


def _set_cached_context(customer_id: str, result):
    """Cache context result."""
    # Limit cache size
    if len(_context_cache) > 1000:
        # Remove oldest entries
        oldest = sorted(_context_cache.items(), key=lambda x: x[1][1])[:100]
        for k, _ in oldest:
            del _context_cache[k]
    _context_cache[customer_id] = (result, time.time())


def invalidate_context_cache(customer_id: str):
    """Invalidate cache when context changes."""
    if customer_id in _context_cache:
        del _context_cache[customer_id]


async def store_message(
    db: AsyncSession,
    customer_id: str,
    channel: str,
    message: str,
    direction: str,
    intent: Optional[str] = None,
    metadata: Optional[dict] = None
) -> StoreContextResponse:
    """
    Store a conversation message.
    Also ensures customer profile exists.
    """
    # Invalidate cache since context is changing
    invalidate_context_cache(customer_id)

    # Ensure customer exists
    await ensure_customer_exists(db, customer_id)

    # Create conversation entry
    conversation = Conversation(
        customer_id=customer_id,
        channel=channel,
        message=message,
        direction=direction,
        intent=intent,
        extra_data=metadata or {}
    )

    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    # Update customer metadata with latest info (non-blocking for performance)
    try:
        await update_customer_metadata(db, customer_id, message, channel)
    except Exception as e:
        logger.warning(f"Failed to update customer metadata: {e}")

    return StoreContextResponse(
        success=True,
        conversation_id=str(conversation.id)
    )


async def ensure_customer_exists(db: AsyncSession, customer_id: str) -> None:
    """Create customer profile if it doesn't exist."""
    stmt = select(Customer).where(Customer.primary_id == customer_id)
    result = await db.execute(stmt)
    customer = result.scalar_one_or_none()

    if not customer:
        customer = Customer(
            primary_id=customer_id,
            linked_ids=[],
            metadata={}
        )
        db.add(customer)
        await db.commit()
        logger.info(f"Created new customer profile: {customer_id}")


async def update_customer_metadata(
    db: AsyncSession,
    customer_id: str,
    message: str,
    channel: str
) -> None:
    """Update customer metadata based on message content."""
    # Detect preferred language
    language = detect_language(message)

    # Get current metadata
    stmt = select(Customer).where(Customer.primary_id == customer_id)
    result = await db.execute(stmt)
    customer = result.scalar_one_or_none()

    if customer:
        metadata = customer.extra_data or {}

        # Update language preference (simple frequency-based)
        lang_counts = metadata.get("language_counts", {})
        lang_counts[language] = lang_counts.get(language, 0) + 1
        metadata["language_counts"] = lang_counts

        # Set preferred language as most frequent
        if lang_counts:
            metadata["preferred_language"] = max(lang_counts, key=lang_counts.get)

        # Update last channel
        metadata["last_channel"] = channel
        metadata["last_interaction"] = datetime.utcnow().isoformat()

        customer.extra_data = metadata
        customer.updated_at = func.now()
        await db.commit()


async def retrieve_context(
    db: AsyncSession,
    customer_id: str,
    limit: int = 20
) -> RetrieveContextResponse:
    """
    Retrieve conversation history and customer metadata.
    Also checks for linked channel IDs.
    OPTIMIZED: Uses in-memory caching.
    """
    # Check cache first
    cached = _get_cached_context(customer_id)
    if cached:
        logger.debug(f"Cache hit for customer: {customer_id}")
        return cached

    # Get customer profile
    stmt = select(Customer).where(
        or_(
            Customer.primary_id == customer_id,
            Customer.linked_ids.contains([customer_id])
        )
    )
    result = await db.execute(stmt)
    customer = result.scalar_one_or_none()

    # Determine all customer IDs to search
    customer_ids = [customer_id]
    if customer:
        customer_ids.append(customer.primary_id)
        if customer.linked_ids:
            customer_ids.extend(customer.linked_ids)
    customer_ids = list(set(customer_ids))  # Remove duplicates

    # Get conversation history
    stmt = (
        select(Conversation)
        .where(Conversation.customer_id.in_(customer_ids))
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    conversations = result.scalars().all()

    # Reverse to get chronological order
    conversations = list(reversed(conversations))

    # Format messages
    messages = [
        MessageInfo(
            message=conv.message,
            direction=conv.direction,
            timestamp=conv.created_at.isoformat(),
            intent=conv.intent
        )
        for conv in conversations
    ]

    # Build customer metadata
    metadata = build_customer_metadata(customer, conversations, customer_ids)

    # Format conversation history for AI
    formatted_for_ai = format_conversation_for_ai(messages)

    result = RetrieveContextResponse(
        customer_id=customer_id,
        messages=messages,
        customer_metadata=metadata,
        formatted_for_ai=formatted_for_ai
    )

    # Cache the result
    _set_cached_context(customer_id, result)

    return result


def build_customer_metadata(
    customer: Optional[Customer],
    conversations: List[Conversation],
    customer_ids: List[str]
) -> CustomerMetadata:
    """Build customer metadata from profile and conversation history."""
    # Default values
    name = None
    phone = None
    preferred_language = "en"
    linked_channels = []

    if customer and customer.extra_data:
        meta = customer.extra_data
        name = meta.get("name")
        phone = meta.get("phone")
        preferred_language = meta.get("preferred_language", "en")

        # Build linked channels list
        if customer.linked_ids:
            linked_channels = customer.linked_ids

    # Extract info from conversations if not in metadata
    if not phone:
        phone = extract_phone_from_conversations(conversations)

    if not name:
        name = extract_name_from_conversations(conversations)

    return CustomerMetadata(
        name=name,
        phone=phone,
        total_interactions=len(conversations),
        preferred_language=preferred_language,
        linked_channels=linked_channels
    )


def extract_phone_from_conversations(conversations: List[Conversation]) -> Optional[str]:
    """Extract phone number from conversation history."""
    import re
    phone_pattern = r'(?:\+?20|0)?1[0125]\d{8}'

    for conv in reversed(conversations):  # Most recent first
        matches = re.findall(phone_pattern, conv.message)
        if matches:
            phone = matches[0]
            # Normalize to +20 format
            if phone.startswith("01"):
                phone = "+20" + phone[1:]
            elif phone.startswith("1"):
                phone = "+20" + phone
            elif not phone.startswith("+"):
                phone = "+" + phone
            return phone
    return None


def extract_name_from_conversations(conversations: List[Conversation]) -> Optional[str]:
    """Extract customer name from conversation history."""
    import re

    name_patterns = [
        r'(?:my name is|اسمي|ana|i\'m|i am)\s+([a-zA-Z\u0600-\u06FF]+)',
        r'(?:name:|الاسم:?)\s+([a-zA-Z\u0600-\u06FF]+)',
    ]

    for conv in reversed(conversations):
        if conv.direction == "incoming":
            for pattern in name_patterns:
                match = re.search(pattern, conv.message, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
    return None


def format_conversation_for_ai(messages: List[MessageInfo]) -> str:
    """Format conversation history for AI prompt injection."""
    if not messages:
        return "No previous conversation history."

    lines = ["CONVERSATION HISTORY:"]

    # Show last 10 messages for context, but deduplicate consecutive identical messages
    recent_messages = messages[-10:]

    prev_message = None
    duplicate_count = 0

    for msg in recent_messages:
        # Skip consecutive duplicate messages
        if prev_message and msg.message == prev_message.message and msg.direction == prev_message.direction:
            duplicate_count += 1
            continue

        # If we had duplicates, add a note
        if duplicate_count > 0:
            lines.append(f"  [... repeated {duplicate_count} more time(s)]")
            duplicate_count = 0

        role = "Customer" if msg.direction == "incoming" else "Assistant"
        timestamp = msg.timestamp[:19].replace("T", " ")  # Simplified timestamp
        # Truncate very long messages
        message_text = msg.message[:500] + "..." if len(msg.message) > 500 else msg.message
        lines.append(f"[{timestamp}] {role}: {message_text}")
        prev_message = msg

    # Handle trailing duplicates
    if duplicate_count > 0:
        lines.append(f"  [... repeated {duplicate_count} more time(s)]")

    return "\n".join(lines)


async def link_channels(
    db: AsyncSession,
    primary_id: str,
    secondary_id: str
) -> LinkChannelsResponse:
    """
    Link two channel IDs as belonging to the same customer.
    Merges conversation history under the primary ID.
    """
    logger.info(f"Linking channels: {primary_id} <-> {secondary_id}")

    # Ensure primary customer exists
    await ensure_customer_exists(db, primary_id)

    # Get primary customer
    stmt = select(Customer).where(Customer.primary_id == primary_id)
    result = await db.execute(stmt)
    primary_customer = result.scalar_one()

    # Add secondary ID to linked_ids if not already there
    linked_ids = primary_customer.linked_ids or []
    if secondary_id not in linked_ids:
        linked_ids.append(secondary_id)
        primary_customer.linked_ids = linked_ids
        await db.commit()

    # Count merged conversations (conversations from secondary_id)
    stmt = select(func.count()).where(Conversation.customer_id == secondary_id)
    result = await db.execute(stmt)
    merged_count = result.scalar() or 0

    logger.info(f"Linked {secondary_id} to {primary_id}, merged {merged_count} conversations")

    return LinkChannelsResponse(
        success=True,
        merged_count=merged_count
    )


async def update_customer_profile(
    db: AsyncSession,
    customer_id: str,
    name: Optional[str] = None,
    phone: Optional[str] = None
) -> None:
    """Update customer profile with extracted information."""
    stmt = select(Customer).where(Customer.primary_id == customer_id)
    result = await db.execute(stmt)
    customer = result.scalar_one_or_none()

    if customer:
        metadata = customer.extra_data or {}

        if name and not metadata.get("name"):
            metadata["name"] = name

        if phone and not metadata.get("phone"):
            metadata["phone"] = phone

        customer.extra_data = metadata
        customer.updated_at = func.now()
        await db.commit()
        logger.info(f"Updated customer profile: {customer_id}")
