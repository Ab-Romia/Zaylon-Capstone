"""
Configuration management using environment variables.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    # Use postgresql+psycopg:// for psycopg3 (recommended, no Rust compilation)
    # Or postgresql+asyncpg:// for asyncpg (requires Rust toolchain)
    database_url: str = "postgresql+psycopg://user:password@localhost:5432/ecommerce_dm"

    # API Security
    api_key: str = "your-secret-api-key"

    # Rate Limiting
    rate_limit_per_minute: int = 100

    # Cache Settings
    default_cache_ttl_hours: int = 24

    # Performance
    max_conversation_history: int = 50
    max_product_search_results: int = 5

    # Analytics
    analytics_retention_days: int = 90

    # CORS
    allowed_origins: str = "*"

    # App Info
    app_name: str = "E-commerce DM Microservice"
    app_version: str = "2.1.0"  # Major refactor with modular architecture
    debug: bool = False

    # RAG System Settings
    # Vector Database (Qdrant)
    qdrant_url: str = "http://localhost:6333"  # Use http://qdrant:6333 for Docker
    qdrant_api_key: Optional[str] = None
    qdrant_collection_products: str = "products"
    qdrant_collection_knowledge: str = "knowledge_base"

    # LLM Provider Choice
    llm_provider: str = "openai"  # Options: "openai" or "gemini"

    # OpenAI Settings
    openai_api_key: Optional[str] = None  # For OpenAI embeddings and agents
    openai_chat_model: str = "gpt-4o"  # Main agent model
    openai_chat_model_mini: str = "gpt-4o-mini"  # Supervisor/routing model

    # Gemini Settings
    gemini_api_key: Optional[str] = None  # For Google Gemini
    gemini_chat_model: str = "gemini-1.5-pro"  # Main agent model (supports 1M context, tool calling)
    gemini_chat_model_mini: str = "gemini-1.5-flash"  # Faster, cheaper model for routing

    # Embeddings
    embedding_model: str = "text-embedding-3-small"  # OpenAI model
    gemini_embedding_model: str = "models/text-embedding-004"  # Gemini embedding model
    local_embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # For Arabic/multilingual
    use_local_embeddings: bool = False  # Set to True to use local models instead of cloud
    embedding_dimension: int = 1536  # OpenAI: 1536, Gemini: 768, local: 384

    # RAG Retrieval Settings
    rag_top_k: int = 5  # Number of documents to retrieve
    rag_similarity_threshold: float = 0.7  # Minimum similarity score
    rag_max_context_length: int = 4000  # Max tokens for context
    rag_chunk_size: int = 500  # Document chunk size for indexing
    rag_chunk_overlap: int = 50  # Overlap between chunks

    # RAG Features
    enable_semantic_search: bool = True  # Use vector search for products
    enable_knowledge_base: bool = True  # Include KB in responses
    enable_hybrid_search: bool = True  # Combine keyword + vector search

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra env vars (e.g., Docker compose vars)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
