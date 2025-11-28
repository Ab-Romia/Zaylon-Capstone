"""
API v1 router aggregation.
Combines all endpoint routers into a single API router.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    health,
    products,
    context,
    intent,
    cache,
    analytics,
    n8n,
    rag,
)

# Create main API v1 router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router)
api_router.include_router(products.router)
api_router.include_router(context.router)
api_router.include_router(intent.router)
api_router.include_router(cache.router)
api_router.include_router(analytics.router)
api_router.include_router(n8n.router)
api_router.include_router(rag.router)
