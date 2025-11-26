"""Product search endpoints."""

import time
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import verify_api_key, limiter, get_rate_limit_string
from app.schemas import ProductSearchRequest, ProductSearchResponse
from app.services import products

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["Products"])


@router.post(
    "/search",
    response_model=ProductSearchResponse,
    summary="Search products with multilingual support"
)
@limiter.limit(get_rate_limit_string())
async def search_products(
    request: Request,
    body: ProductSearchRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Search products using multilingual keyword matching.

    Supports:
    - Arabic: جينز, بنطلون, هودي, شيرت
    - Franco-Arabic: jeans, pants, 7ezaa2, azra2
    - English: jeans, pants, hoodie, shirt

    Returns relevant products formatted for AI context injection.
    """
    start_time = time.time()

    result = await products.search_products(
        db=db,
        query=body.query,
        limit=body.limit
    )

    elapsed_ms = int((time.time() - start_time) * 1000)
    logger.info(f"Product search completed in {elapsed_ms}ms")

    return result
