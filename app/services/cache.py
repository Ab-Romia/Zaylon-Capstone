"""
Response caching service.
Caches common responses to reduce AI API calls.
"""
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ResponseCache
from app.schemas import CacheCheckResponse, CacheStoreResponse
import logging

logger = logging.getLogger(__name__)


def normalize_message(message: str) -> str:
    """
    Normalize message for cache key generation.

    - Lowercase
    - Remove extra whitespace
    - Remove emojis
    - Remove punctuation except spaces
    """
    # Lowercase
    normalized = message.lower()

    # Remove emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    normalized = emoji_pattern.sub('', normalized)

    # Remove punctuation except Arabic characters
    normalized = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', normalized)

    # Normalize whitespace
    normalized = ' '.join(normalized.split())

    return normalized.strip()


def hash_message(normalized_message: str) -> str:
    """Generate MD5 hash of normalized message."""
    return hashlib.md5(normalized_message.encode('utf-8')).hexdigest()


async def check_cache(
    db: AsyncSession,
    message: str,
    max_age_hours: int = 24
) -> CacheCheckResponse:
    """
    Check if a cached response exists for the message.

    Returns:
        CacheCheckResponse with cached response if found
    """
    normalized = normalize_message(message)
    message_hash = hash_message(normalized)

    logger.debug(f"Checking cache for hash: {message_hash}")

    # Query cache
    stmt = select(ResponseCache).where(
        ResponseCache.message_hash == message_hash,
        ResponseCache.expires_at > datetime.utcnow()
    )

    result = await db.execute(stmt)
    cached = result.scalar_one_or_none()

    if cached:
        # Update hit count
        cached.hit_count += 1
        await db.commit()

        # Estimate saved tokens (rough estimate: 1 token per 4 chars)
        saved_tokens = len(cached.cached_response) // 4

        logger.info(f"Cache hit! Saved ~{saved_tokens} tokens")

        return CacheCheckResponse(
            cached=True,
            response=cached.cached_response,
            confidence=0.95,  # High confidence for cached responses
            saved_tokens=saved_tokens
        )

    logger.debug("Cache miss")
    return CacheCheckResponse(
        cached=False,
        response=None,
        confidence=None,
        saved_tokens=None
    )


async def store_cache(
    db: AsyncSession,
    message: str,
    response: str,
    intent: str,
    ttl_hours: int = 24
) -> CacheStoreResponse:
    """
    Store a response in cache.

    Only caches certain types of responses:
    - Static info (greetings, thanks)
    - Product information that doesn't change often
    - NOT order confirmations or personalized responses
    """
    # Don't cache very short messages or responses
    if len(message) < 3 or len(response) < 10:
        return CacheStoreResponse(success=False)

    # Don't cache personalized responses
    if any(word in response.lower() for word in ["your order", "order #", "confirmation"]):
        return CacheStoreResponse(success=False)

    normalized = normalize_message(message)
    message_hash = hash_message(normalized)
    expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)

    logger.info(f"Storing in cache with TTL {ttl_hours}h")

    # Upsert pattern
    stmt = select(ResponseCache).where(ResponseCache.message_hash == message_hash)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing cache entry
        existing.cached_response = response
        existing.intent = intent
        existing.expires_at = expires_at
        existing.hit_count += 1
    else:
        # Create new cache entry
        cache_entry = ResponseCache(
            message_hash=message_hash,
            normalized_message=normalized,
            cached_response=response,
            intent=intent,
            expires_at=expires_at
        )
        db.add(cache_entry)

    await db.commit()

    return CacheStoreResponse(success=True)


async def cleanup_expired_cache(db: AsyncSession) -> int:
    """Remove expired cache entries. Returns number of entries removed."""
    stmt = delete(ResponseCache).where(
        ResponseCache.expires_at < datetime.utcnow()
    )
    result = await db.execute(stmt)
    await db.commit()

    deleted_count = result.rowcount
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} expired cache entries")

    return deleted_count


async def get_cache_stats(db: AsyncSession) -> dict:
    """Get cache statistics."""
    from sqlalchemy import func

    # Total entries
    stmt = select(func.count()).select_from(ResponseCache)
    result = await db.execute(stmt)
    total_entries = result.scalar() or 0

    # Total hits
    stmt = select(func.sum(ResponseCache.hit_count)).select_from(ResponseCache)
    result = await db.execute(stmt)
    total_hits = result.scalar() or 0

    # Expired entries
    stmt = select(func.count()).select_from(ResponseCache).where(
        ResponseCache.expires_at < datetime.utcnow()
    )
    result = await db.execute(stmt)
    expired_entries = result.scalar() or 0

    return {
        "total_entries": total_entries,
        "total_hits": total_hits,
        "expired_entries": expired_entries,
        "active_entries": total_entries - expired_entries
    }
