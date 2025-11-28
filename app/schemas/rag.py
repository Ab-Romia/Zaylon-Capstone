"""RAG system schemas."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


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
