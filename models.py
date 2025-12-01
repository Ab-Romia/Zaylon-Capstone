"""
Pydantic models for request/response validation.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Product Search Models
# ============================================================================

class ProductSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Search query in Arabic, Franco-Arabic, or English")
    limit: int = Field(default=3, ge=1, le=20, description="Maximum number of products to return")


class ProductInfo(BaseModel):
    id: str
    name: str
    price: float
    sizes: List[str]
    colors: List[str]
    stock_count: int
    description: str


class SearchMetadata(BaseModel):
    detected_language: str
    matched_keywords: List[str]
    total_found: int


class ProductSearchResponse(BaseModel):
    products: List[ProductInfo]
    formatted_for_ai: str
    search_metadata: SearchMetadata


# ============================================================================
# Conversation Context Models
# ============================================================================

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


# ============================================================================
# Intent Classification Models
# ============================================================================

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


# ============================================================================
# Response Cache Models
# ============================================================================

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


# ============================================================================
# Analytics Models
# ============================================================================

class AnalyticsLogRequest(BaseModel):
    customer_id: str
    event_type: str = Field(..., description="Event type: message_received, intent_classified, order_created, etc.")
    event_data: Dict[str, Any]
    response_time_ms: Optional[int] = None
    ai_tokens_used: Optional[int] = None


class AnalyticsLogResponse(BaseModel):
    success: bool


class TopIntent(BaseModel):
    intent: str
    count: int
    percentage: float


class TopProduct(BaseModel):
    product: str
    count: int


class AnalyticsDashboardResponse(BaseModel):
    total_messages: int
    total_orders: int
    conversion_rate: float
    avg_response_time_ms: float
    messages_by_channel: Dict[str, int]
    top_intents: List[TopIntent]
    top_products_inquired: List[TopProduct]
    ai_cost_estimate: float
    cache_hit_rate: float


# ============================================================================
# n8n Integration Models
# ============================================================================

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


# ============================================================================
# Common Response Models
# ============================================================================

class ErrorResponse(BaseModel):
    error: str
    detail: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class HealthCheckResponse(BaseModel):
    status: str
    version: str
    database: str
    timestamp: str
    qdrant: Optional[str] = None  # RAG: Vector database status


# ============================================================================
# RAG System Models
# ============================================================================

class IndexProductRequest(BaseModel):
    product_id: str = Field(..., description="Product ID to index")


class IndexProductResponse(BaseModel):
    success: bool
    product_id: str
    message: str


class IndexAllProductsResponse(BaseModel):
    success: bool
    total: int
    indexed: int
    failed: int
    start_time: str
    end_time: Optional[str] = None
    error: Optional[str] = None


class IndexKnowledgeRequest(BaseModel):
    doc_id: str = Field(..., description="Unique document ID")
    content: str = Field(..., min_length=1, description="Document content")
    title: Optional[str] = None
    category: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IndexKnowledgeResponse(BaseModel):
    success: bool
    doc_id: str
    chunks_created: int
    message: str


class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)
    include_knowledge: bool = Field(default=True, description="Include knowledge base results")
    search_method: str = Field(
        default="hybrid",
        pattern="^(semantic|keyword|hybrid)$",
        description="Search method: semantic, keyword, or hybrid"
    )


class RAGProductResult(BaseModel):
    id: str
    name: str
    price: float
    description: str
    sizes: List[str]
    colors: List[str]
    stock_count: int
    similarity_score: float
    search_method: str


class RAGKnowledgeResult(BaseModel):
    doc_id: str
    content: str
    title: Optional[str] = None
    category: Optional[str] = None
    similarity_score: float


class RAGSearchResponse(BaseModel):
    products: List[RAGProductResult]
    products_formatted: str
    knowledge_items: List[RAGKnowledgeResult]
    knowledge_formatted: str
    metadata: Dict[str, Any]
    rag_enabled: bool


class VectorDBStatusResponse(BaseModel):
    connected: bool
    products_collection: Optional[Dict[str, Any]] = None
    knowledge_collection: Optional[Dict[str, Any]] = None
    embedding_dimension: int
    embedding_model: str


class EmbedTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class EmbedTextResponse(BaseModel):
    embedding: List[float]
    dimension: int
    model: str


# Enhanced PrepareContextResponse with RAG
class PrepareContextResponseRAG(BaseModel):
    conversation_history: str
    relevant_products: str
    intent_analysis: IntentClassifyResponse
    cached_response: Optional[str] = None
    skip_ai: bool
    customer_metadata: CustomerMetadata
    # RAG additions
    rag_context: Optional[RAGSearchResponse] = None
    rag_enabled: bool = False


# ============================================================================
# Order Management Models
# ============================================================================

class CreateOrderRequest(BaseModel):
    customer_id: str = Field(..., description="Customer identifier")
    channel: str = Field(..., pattern="^(instagram|whatsapp)$")
    product_id: str = Field(..., description="Product UUID")
    product_name: str
    size: str
    color: str
    quantity: int = Field(default=1, ge=1)
    total_price: float = Field(..., gt=0)
    customer_name: str
    phone: str
    address: str


class CreateOrderResponse(BaseModel):
    success: bool
    order_id: Optional[str] = None
    error: Optional[str] = None
    message: str


class CustomerOrderHistory(BaseModel):
    order_id: str
    product_name: str
    total_price: float
    status: str
    created_at: str


class EnhancedCustomerMetadata(BaseModel):
    name: Optional[str]
    phone: Optional[str]
    total_interactions: int
    preferred_language: str
    linked_channels: List[str]
    # Enhanced fields
    total_orders: int = 0
    total_spent: float = 0.0
    last_order_date: Optional[str] = None
    recent_orders: List[CustomerOrderHistory] = []


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


# ============================================================================
# Agentic System Models (Zaylon v2 API)
# ============================================================================

class AgentInvokeRequest(BaseModel):
    """Request model for agent invocation."""
    customer_id: str = Field(..., min_length=1, description="Customer identifier (e.g., 'instagram:@username')")
    message: str = Field(..., min_length=1, max_length=5000, description="User's message")
    channel: str = Field(..., pattern="^(instagram|whatsapp)$", description="Communication channel")
    thread_id: Optional[str] = Field(default=None, description="Optional thread ID for conversation persistence")


class AgentThought(BaseModel):
    """Individual reasoning step in the agent's chain of thought."""
    node: str = Field(..., description="Node name (e.g., 'supervisor', 'sales_agent')")
    reasoning: str = Field(..., description="Agent's reasoning at this step")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AgentToolCall(BaseModel):
    """Record of a tool invocation by an agent."""
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None
    success: bool = True


class AgentInvokeResponse(BaseModel):
    """Response model for agent invocation."""
    success: bool
    response: str = Field(..., description="Final response from the agent")
    agent_used: str = Field(..., description="Which agent handled the request (sales/support)")
    chain_of_thought: List[AgentThought] = Field(default_factory=list, description="Full reasoning chain")
    tool_calls: List[AgentToolCall] = Field(default_factory=list, description="Tools invoked during execution")
    user_profile: Dict[str, Any] = Field(default_factory=dict, description="Customer facts from Memory Bank")
    execution_time_ms: int = Field(..., ge=0, description="Total execution time")
    thread_id: str = Field(..., description="Thread ID for conversation continuity")
    error: Optional[str] = None


class AgentStreamChunk(BaseModel):
    """Streaming response chunk for agent invocation."""
    type: str = Field(..., description="Chunk type: 'thought', 'tool_call', 'response', 'final'")
    content: Optional[str] = None
    node: Optional[str] = None
    tool_name: Optional[str] = None
    done: bool = False
