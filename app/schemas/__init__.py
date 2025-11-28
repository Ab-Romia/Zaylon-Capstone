"""
Pydantic schemas for request/response validation.
All schemas are organized by domain and exported here for easy importing.
"""

# Product schemas
from .products import (
    ProductSearchRequest,
    ProductSearchResponse,
    ProductInfo,
    SearchMetadata,
)

# Context schemas
from .context import (
    StoreContextRequest,
    StoreContextResponse,
    MessageInfo,
    CustomerMetadata,
    RetrieveContextResponse,
    LinkChannelsRequest,
    LinkChannelsResponse,
)

# Intent schemas
from .intent import (
    IntentClassifyRequest,
    IntentClassifyResponse,
    ExtractedEntities,
)

# Cache schemas
from .cache import (
    CacheCheckRequest,
    CacheCheckResponse,
    CacheStoreRequest,
    CacheStoreResponse,
)

# Analytics schemas
from .analytics import (
    AnalyticsLogRequest,
    AnalyticsLogResponse,
    TopIntent,
    TopProduct,
    AnalyticsDashboardResponse,
)

# Order schemas
from .orders import (
    CreateOrderRequest,
    CreateOrderResponse,
    CustomerOrderHistory,
    EnhancedCustomerMetadata,
)

# RAG schemas
from .rag import (
    IndexProductRequest,
    IndexProductResponse,
    IndexAllProductsResponse,
    IndexKnowledgeRequest,
    IndexKnowledgeResponse,
    RAGSearchRequest,
    RAGProductResult,
    RAGKnowledgeResult,
    RAGSearchResponse,
    VectorDBStatusResponse,
    EmbedTextRequest,
    EmbedTextResponse,
)

# n8n integration schemas
from .n8n import (
    PrepareContextRequest,
    PrepareContextResponse,
    PrepareContextResponseRAG,
    PrepareContextEnhancedRequest,
    PrepareContextEnhancedResponse,
    StoreInteractionRequest,
    StoreInteractionResponse,
    ProcessCompleteRequest,
    ProcessCompleteResponse,
)

# Common schemas
from .common import (
    ErrorResponse,
    HealthCheckResponse,
)

__all__ = [
    # Products
    "ProductSearchRequest",
    "ProductSearchResponse",
    "ProductInfo",
    "SearchMetadata",
    # Context
    "StoreContextRequest",
    "StoreContextResponse",
    "MessageInfo",
    "CustomerMetadata",
    "RetrieveContextResponse",
    "LinkChannelsRequest",
    "LinkChannelsResponse",
    # Intent
    "IntentClassifyRequest",
    "IntentClassifyResponse",
    "ExtractedEntities",
    # Cache
    "CacheCheckRequest",
    "CacheCheckResponse",
    "CacheStoreRequest",
    "CacheStoreResponse",
    # Analytics
    "AnalyticsLogRequest",
    "AnalyticsLogResponse",
    "TopIntent",
    "TopProduct",
    "AnalyticsDashboardResponse",
    # Orders
    "CreateOrderRequest",
    "CreateOrderResponse",
    "CustomerOrderHistory",
    "EnhancedCustomerMetadata",
    # RAG
    "IndexProductRequest",
    "IndexProductResponse",
    "IndexAllProductsResponse",
    "IndexKnowledgeRequest",
    "IndexKnowledgeResponse",
    "RAGSearchRequest",
    "RAGProductResult",
    "RAGKnowledgeResult",
    "RAGSearchResponse",
    "VectorDBStatusResponse",
    "EmbedTextRequest",
    "EmbedTextResponse",
    # n8n
    "PrepareContextRequest",
    "PrepareContextResponse",
    "PrepareContextResponseRAG",
    "PrepareContextEnhancedRequest",
    "PrepareContextEnhancedResponse",
    "StoreInteractionRequest",
    "StoreInteractionResponse",
    "ProcessCompleteRequest",
    "ProcessCompleteResponse",
    # Common
    "ErrorResponse",
    "HealthCheckResponse",
]
