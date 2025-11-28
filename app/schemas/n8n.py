"""n8n integration schemas."""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from .context import CustomerMetadata
from .orders import EnhancedCustomerMetadata
from .intent import IntentClassifyResponse
from .rag import RAGSearchResponse


class PrepareContextRequest(BaseModel):
    customer_id: str
    message: str = Field(..., min_length=1, max_length=5000)
    channel: str = Field(..., pattern="^(instagram|whatsapp)$")


class PrepareContextResponse(BaseModel):
    conversation_history: str
    relevant_products: str
    intent_analysis: IntentClassifyResponse
    cached_response: Optional[str] = None
    skip_ai: bool
    customer_metadata: CustomerMetadata


class PrepareContextResponseRAG(BaseModel):
    """Enhanced PrepareContextResponse with RAG."""
    conversation_history: str
    relevant_products: str
    intent_analysis: IntentClassifyResponse
    cached_response: Optional[str] = None
    skip_ai: bool
    customer_metadata: CustomerMetadata
    rag_context: Optional[RAGSearchResponse] = None
    rag_enabled: bool = False


class PrepareContextEnhancedRequest(BaseModel):
    customer_id: str
    message: str = Field(..., min_length=1, max_length=5000)
    channel: str = Field(..., pattern="^(instagram|whatsapp)$")


class PrepareContextEnhancedResponse(BaseModel):
    conversation_history: str
    relevant_products: str
    intent_analysis: IntentClassifyResponse
    cached_response: Optional[str] = None
    skip_ai: bool
    customer_metadata: EnhancedCustomerMetadata
    customer_order_history: str
    rag_enabled: bool = False


class StoreInteractionRequest(BaseModel):
    customer_id: str
    channel: str = Field(..., pattern="^(instagram|whatsapp)$")
    user_message: str
    ai_response: str
    intent: str
    action: str = Field(..., description="Action taken: answer, create_order, request_info, etc.")
    order_data: Optional[Dict[str, Any]] = None
    response_time_ms: int = Field(..., ge=0)
    ai_tokens_used: Optional[int] = None


class StoreInteractionResponse(BaseModel):
    success: bool


class ProcessCompleteRequest(BaseModel):
    """Combined request for streamlined endpoint."""
    customer_id: str
    message: str
    channel: str = Field(..., pattern="^(instagram|whatsapp)$")
    ai_response: Optional[str] = None
    action: Optional[str] = None
    order_data: Optional[Dict[str, Any]] = None
    tokens_used: int = 0
    response_time_ms: int = 0


class ProcessCompleteResponse(BaseModel):
    """Combined response for streamlined endpoint."""
    conversation_history: str
    relevant_products: str
    customer_order_history: str
    intent: str
    confidence: float
    entities: Dict[str, Any]
    customer_name: Optional[str]
    customer_phone: Optional[str]
    total_orders: int
    total_spent: float
    preferred_language: str
    skip_ai: bool
    cached_response: Optional[str]
    order_created: bool = False
    order_id: Optional[str] = None
    order_error: Optional[str] = None
    final_response: Optional[str] = None
