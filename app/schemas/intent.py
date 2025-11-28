"""Intent classification schemas."""
from typing import Optional, List
from pydantic import BaseModel, Field


class IntentClassifyRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    context: Optional[List[str]] = Field(default=None, description="Previous messages for context")


class ExtractedEntities(BaseModel):
    product_name: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    quantity: Optional[int] = None
    phone: Optional[str] = None


class IntentClassifyResponse(BaseModel):
    intent: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    entities: ExtractedEntities
    skip_ai: bool
    suggested_response: Optional[str] = None
