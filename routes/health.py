"""Health check endpoint."""

from datetime import datetime
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from models import HealthCheckResponse
from services import get_vector_db

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check service health and database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"

    qdrant_status = "not_configured"
    try:
        vector_db = get_vector_db()
        if vector_db.is_connected():
            qdrant_status = "connected"
        else:
            qdrant_status = "disconnected"
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        qdrant_status = "error"

    overall_status = "healthy" if db_status == "connected" else "degraded"
    if qdrant_status == "disconnected":
        overall_status = "degraded"

    return HealthCheckResponse(
        status=overall_status,
        version=settings.app_version,
        database=db_status,
        qdrant=qdrant_status,
        timestamp=datetime.utcnow().isoformat()
    )
