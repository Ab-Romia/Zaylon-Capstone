"""Response cache schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class CacheCheckRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    max_age_hours: int = Field(default=24, ge=1, le=720)


class CacheCheckResponse(BaseModel):
    cached: bool
    response: Optional[str] = None
    confidence: Optional[float] = None
    saved_tokens: Optional[int] = None


class CacheStoreRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    response: str = Field(..., min_length=1, max_length=10000)
    intent: str
    ttl_hours: int = Field(default=24, ge=1, le=720)


class CacheStoreResponse(BaseModel):
    success: bool
