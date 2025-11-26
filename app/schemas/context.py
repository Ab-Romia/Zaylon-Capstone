"""Conversation context schemas."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class StoreContextRequest(BaseModel):
    customer_id: str = Field(..., min_length=1, description="Customer identifier (e.g., 'instagram:@username')")
    channel: str = Field(..., pattern="^(instagram|whatsapp)$")
    message: str = Field(..., min_length=1, max_length=5000)
    direction: str = Field(..., pattern="^(incoming|outgoing)$")
    intent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class StoreContextResponse(BaseModel):
    success: bool
    conversation_id: str


class MessageInfo(BaseModel):
    message: str
    direction: str
    timestamp: str
    intent: Optional[str]


class CustomerMetadata(BaseModel):
    name: Optional[str]
    phone: Optional[str]
    total_interactions: int
    preferred_language: str
    linked_channels: List[str]


class RetrieveContextResponse(BaseModel):
    customer_id: str
    messages: List[MessageInfo]
    customer_metadata: CustomerMetadata
    formatted_for_ai: str


class LinkChannelsRequest(BaseModel):
    primary_id: str
    secondary_id: str


class LinkChannelsResponse(BaseModel):
    success: bool
    merged_count: int
