"""
E-commerce DM Microservice - FastAPI Application
Main entry point with modular route organization.
"""
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.db import init_db, close_db
from app.core.security import limiter
from app.schemas import ErrorResponse
from app.core.background import background_tasks
from app.services import (
    get_embedding_service, get_vector_db, init_vector_db, close_vector_db
)
from app.api.v1.router import api_router

# Import agent v2 router from root-level routes
# (Agent v2 is mounted separately with /api/v2 prefix, not under /api/v1)
import sys
from pathlib import Path
# Add root directory to path to import from routes module
sys.path.insert(0, str(Path(__file__).parent.parent))
from routes.agent import router as agent_v2_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting E-commerce DM Microservice with RAG support...")
    await init_db()
    logger.info("Database initialized")

    # Initialize background task manager
    await background_tasks.start()
    logger.info("Background task manager started")

    # Initialize RAG system
    try:
        embedding_service = get_embedding_service()
        embedding_dim = embedding_service.get_dimension()
        logger.info(f"Embedding service initialized (dimension: {embedding_dim})")

        vector_db = get_vector_db()
        if vector_db.is_connected():
            await init_vector_db(embedding_dim)
            logger.info("Vector database (Qdrant) initialized")
        else:
            logger.warning("Vector database not connected - RAG features will be limited")
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}")
        logger.warning("Service will continue without RAG features")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await background_tasks.stop()
    await close_db()
    await close_vector_db()
    logger.info("All connections closed")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered microservice for e-commerce Instagram/WhatsApp DM automation",
    lifespan=lifespan
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Error Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=str(exc.detail),
            timestamp=datetime.utcnow().isoformat()
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc) if settings.debug else "An unexpected error occurred",
            timestamp=datetime.utcnow().isoformat()
        ).model_dump()
    )


# Include API v1 router
app.include_router(api_router, prefix="/api/v1")

# Include Agent v2 router (mounted at root level with its own /api/v2 prefix)
app.include_router(agent_v2_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        workers=1
    )
