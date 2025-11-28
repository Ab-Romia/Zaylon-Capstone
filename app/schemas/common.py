"""Common response schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str
    detail: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class HealthCheckResponse(BaseModel):
    status: str
    version: str
    database: str
    timestamp: str
    qdrant: Optional[str] = None
