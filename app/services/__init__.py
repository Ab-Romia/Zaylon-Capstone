# Services package

# Import RAG services first (they don't depend on other services)
from . import embeddings
from . import vector_db
from . import ingestion

# Import existing services
from . import products
from . import context
from . import intent
from . import cache
from . import analytics

# Import RAG orchestration last (depends on products)
from . import rag

# Export service getters
from .embeddings import get_embedding_service
from .vector_db import get_vector_db, init_vector_db, close_vector_db
from .ingestion import get_ingestion_service
from .rag import get_rag_service

__all__ = [
    "products",
    "context",
    "intent",
    "cache",
    "analytics",
    "embeddings",
    "vector_db",
    "ingestion",
    "rag",
    "get_embedding_service",
    "get_vector_db",
    "init_vector_db",
    "close_vector_db",
    "get_ingestion_service",
    "get_rag_service",
]
