"""Analytics endpoints."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import verify_api_key, limiter, get_rate_limit_string
from app.schemas import (
    AnalyticsLogRequest, AnalyticsLogResponse,
    AnalyticsDashboardResponse
)
from app.services import analytics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.post(
    "/log",
    response_model=AnalyticsLogResponse,
    summary="Log analytics event"
)
@limiter.limit(get_rate_limit_string())
async def log_analytics(
    request: Request,
    body: AnalyticsLogRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Log an analytics event.

    Event types: message_received, intent_classified, cache_hit,
    cache_miss, order_created, product_searched, etc.
    """
    return await analytics.log_event(
        db=db,
        customer_id=body.customer_id,
        event_type=body.event_type,
        event_data=body.event_data,
        response_time_ms=body.response_time_ms,
        ai_tokens_used=body.ai_tokens_used
    )


@router.get(
    "/dashboard",
    response_model=AnalyticsDashboardResponse,
    summary="Get analytics dashboard"
)
@limiter.limit(get_rate_limit_string())
async def get_dashboard(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get analytics dashboard with key metrics.

    Includes: total messages, orders, conversion rate, response times,
    top intents, popular products, AI cost estimate, cache hit rate.
    """
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None

    return await analytics.get_dashboard(
        db=db,
        start_date=start_dt,
        end_date=end_dt
    )
