"""Response cache endpoints."""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import verify_api_key, limiter, get_rate_limit_string
from app.schemas import (
    CacheCheckRequest, CacheCheckResponse,
    CacheStoreRequest, CacheStoreResponse
)
from app.services import cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["Cache"])


@router.post(
    "/check",
    response_model=CacheCheckResponse,
    summary="Check for cached response"
)
@limiter.limit(get_rate_limit_string())
async def check_cache(
    request: Request,
    body: CacheCheckRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Check if a cached response exists for the message.

    Normalizes message and checks against cache.
    Returns saved tokens estimate if cache hit.
    """
    return await cache.check_cache(
        db=db,
        message=body.message,
        max_age_hours=body.max_age_hours
    )


@router.post(
    "/store",
    response_model=CacheStoreResponse,
    summary="Store response in cache"
)
@limiter.limit(get_rate_limit_string())
async def store_cache(
    request: Request,
    body: CacheStoreRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Store a response in cache with TTL.

    Automatically skips personalized responses (order confirmations, etc.).
    """
    return await cache.store_cache(
        db=db,
        message=body.message,
        response=body.response,
        intent=body.intent,
        ttl_hours=body.ttl_hours
    )
