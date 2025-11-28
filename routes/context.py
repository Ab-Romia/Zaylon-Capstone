"""Conversation context management endpoints."""

import logging

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import verify_api_key, limiter, get_rate_limit_string
from models import (
    StoreContextRequest, StoreContextResponse,
    RetrieveContextResponse, LinkChannelsRequest, LinkChannelsResponse
)
from services import context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/context", tags=["Context"])


@router.post(
    "/store",
    response_model=StoreContextResponse,
    summary="Store conversation message"
)
@limiter.limit(get_rate_limit_string())
async def store_context(
    request: Request,
    body: StoreContextRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Store a conversation message with metadata."""
    return await context.store_message(
        db=db,
        customer_id=body.customer_id,
        channel=body.channel,
        message=body.message,
        direction=body.direction,
        intent=body.intent,
        metadata=body.metadata
    )


@router.get(
    "/retrieve",
    response_model=RetrieveContextResponse,
    summary="Retrieve conversation history"
)
@limiter.limit(get_rate_limit_string())
async def retrieve_context(
    request: Request,
    customer_id: str = Query(..., description="Customer identifier"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of messages to retrieve"),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Retrieve conversation history and customer metadata.

    Automatically handles cross-channel linking (Instagram + WhatsApp).
    Returns formatted history ready for AI prompt injection.
    """
    return await context.retrieve_context(
        db=db,
        customer_id=customer_id,
        limit=limit
    )


@router.post(
    "/link-channels",
    response_model=LinkChannelsResponse,
    summary="Link customer channels"
)
@limiter.limit(get_rate_limit_string())
async def link_channels(
    request: Request,
    body: LinkChannelsRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Link two channel IDs as belonging to the same customer.

    Example: Link instagram:@user with whatsapp:+201234567890
    """
    return await context.link_channels(
        db=db,
        primary_id=body.primary_id,
        secondary_id=body.secondary_id
    )
