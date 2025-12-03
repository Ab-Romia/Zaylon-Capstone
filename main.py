"""
E-commerce DM Microservice - FastAPI Application
Main entry point with modular route organization.
"""
import logging
import warnings
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from pathlib import Path

from config import get_settings
from database import init_db, close_db
from auth import limiter
from models import ErrorResponse
from core.background import background_tasks
from services import (
    get_embedding_service, get_vector_db, init_vector_db, close_vector_db
)
from routes import (
    health_router, products_router, context_router, intent_router,
    cache_router, analytics_router, n8n_router, rag_router, agent_router
)

# Suppress Pydantic validation warnings from Qdrant client
# These are harmless warnings about extra fields in Qdrant's config responses
warnings.filterwarnings("ignore", message=".*Extra inputs are not permitted.*")
warnings.filterwarnings("ignore", message=".*Input should be a valid integer.*")

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

            # Populate knowledge base with FAQs
            try:
                from scripts.populate_knowledge_base import populate_knowledge_base
                success, failed = await populate_knowledge_base()
                logger.info(f"Knowledge base populated: {success} docs indexed, {failed} failed")
            except Exception as kb_error:
                logger.warning(f"Knowledge base population skipped: {kb_error}")
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


# Include routers
app.include_router(health_router)
app.include_router(products_router)
app.include_router(context_router)
app.include_router(intent_router)
app.include_router(cache_router)
app.include_router(analytics_router)
app.include_router(n8n_router)
app.include_router(rag_router)
app.include_router(agent_router)  # Zaylon v2 agentic API

# Serve frontend static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    # Serve index.html at root
    @app.get("/")
    async def serve_home():
        """Serve the web interface."""
        return FileResponse(str(static_path / "index.html"))

    # Mount static directory for any other static assets
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    logger.info(f"Web interface available at {static_path}")
else:
    logger.warning("Static directory not found. Web interface unavailable.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        workers=1
    )
