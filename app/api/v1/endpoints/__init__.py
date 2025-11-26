"""Route modules for the FastAPI application."""

from .health import router as health_router
from .products import router as products_router
from .context import router as context_router
from .intent import router as intent_router
from .cache import router as cache_router
from .analytics import router as analytics_router
from .n8n import router as n8n_router
from .rag import router as rag_router

__all__ = [
    "health_router",
    "products_router",
    "context_router",
    "intent_router",
    "cache_router",
    "analytics_router",
    "n8n_router",
    "rag_router",
]
