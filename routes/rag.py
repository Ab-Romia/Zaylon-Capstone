"""RAG system endpoints."""

import logging

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db, Product
from auth import verify_api_key, limiter, get_rate_limit_string
from models import (
    IndexProductRequest, IndexProductResponse, IndexAllProductsResponse,
    IndexKnowledgeRequest, IndexKnowledgeResponse,
    RAGSearchRequest, RAGSearchResponse, RAGProductResult, RAGKnowledgeResult,
    VectorDBStatusResponse, EmbedTextRequest, EmbedTextResponse
)
from services import (
    get_embedding_service, get_vector_db, get_ingestion_service, get_rag_service
)

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/rag", tags=["RAG System"])


@router.post(
    "/search",
    response_model=RAGSearchResponse,
    summary="RAG-powered semantic search"
)
@limiter.limit(get_rate_limit_string())
async def rag_search(
    request: Request,
    body: RAGSearchRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Perform RAG-powered semantic search across products and knowledge base.

    This endpoint uses vector embeddings to find semantically similar products
    and knowledge base articles, providing better results than keyword matching alone.
    """
    rag_service = get_rag_service()

    if body.search_method == "semantic":
        # Semantic search only
        products_list = await rag_service.search_products_semantic(
            body.query, db, limit=body.limit
        )
        knowledge_items = []
        if body.include_knowledge:
            knowledge_items = await rag_service.search_knowledge_base(
                body.query, limit=3
            )

        products_formatted = rag_service.format_products_for_ai(products_list)
        knowledge_formatted = rag_service.format_knowledge_for_ai(knowledge_items)

        return RAGSearchResponse(
            products=[RAGProductResult(**p) for p in products_list],
            products_formatted=products_formatted,
            knowledge_items=[RAGKnowledgeResult(**k) for k in knowledge_items],
            knowledge_formatted=knowledge_formatted,
            metadata={
                "search_method": "semantic",
                "total_found": len(products_list)
            },
            rag_enabled=True
        )

    elif body.search_method == "keyword":
        # Keyword search only
        products_list = await rag_service.search_products_keyword(
            body.query, db, limit=body.limit
        )

        products_formatted = rag_service.format_products_for_ai(products_list)

        return RAGSearchResponse(
            products=[RAGProductResult(**p) for p in products_list],
            products_formatted=products_formatted,
            knowledge_items=[],
            knowledge_formatted="",
            metadata={
                "search_method": "keyword",
                "total_found": len(products_list)
            },
            rag_enabled=False
        )

    else:
        # Hybrid search (default)
        rag_context = await rag_service.prepare_rag_context(
            body.query, db, include_knowledge=body.include_knowledge
        )

        return RAGSearchResponse(
            products=[RAGProductResult(**p) for p in rag_context["products"]],
            products_formatted=rag_context["products_formatted"],
            knowledge_items=[RAGKnowledgeResult(**k) for k in rag_context["knowledge_items"]],
            knowledge_formatted=rag_context["knowledge_formatted"],
            metadata=rag_context["product_metadata"],
            rag_enabled=True
        )


@router.post(
    "/index/product",
    response_model=IndexProductResponse,
    summary="Index a single product"
)
@limiter.limit(get_rate_limit_string())
async def index_product(
    request: Request,
    body: IndexProductRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Index a single product into the vector database.

    Use this endpoint when adding or updating a product to make it searchable
    via semantic search.
    """
    ingestion_service = get_ingestion_service()

    # Get product from database with error handling
    try:
        product_id_int = int(body.product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid product_id: must be a number")

    stmt = select(Product).where(Product.id == product_id_int)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product not found: {body.product_id}")

    success = await ingestion_service.index_product(product)

    return IndexProductResponse(
        success=success,
        product_id=body.product_id,
        message="Product indexed successfully" if success else "Failed to index product"
    )


@router.post(
    "/index/products/all",
    response_model=IndexAllProductsResponse,
    summary="Index all products"
)
@limiter.limit("5/hour")
async def index_all_products(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Index all active products into the vector database.

    This is a resource-intensive operation. Use it when:
    - Setting up RAG for the first time
    - Rebuilding the index after major changes
    - Periodically (e.g., daily) to keep index fresh

    Rate limited to 5 requests per hour.
    """
    ingestion_service = get_ingestion_service()
    stats = await ingestion_service.index_all_products(db)

    return IndexAllProductsResponse(**stats, success=True)


@router.post(
    "/index/knowledge",
    response_model=IndexKnowledgeResponse,
    summary="Index a knowledge base document"
)
@limiter.limit(get_rate_limit_string())
async def index_knowledge(
    request: Request,
    body: IndexKnowledgeRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Index a knowledge base document (FAQ, policy, guide, etc.).

    Documents are automatically chunked for optimal retrieval.
    Use this to add FAQs, shipping policies, return policies, etc.
    """
    ingestion_service = get_ingestion_service()

    metadata = body.metadata or {}
    if body.title:
        metadata["title"] = body.title
    if body.category:
        metadata["category"] = body.category

    success = await ingestion_service.index_knowledge_document(
        doc_id=body.doc_id,
        content=body.content,
        metadata=metadata
    )

    # Calculate chunks created (simplified)
    chunks_created = len(body.content) // settings.rag_chunk_size + 1

    return IndexKnowledgeResponse(
        success=success,
        doc_id=body.doc_id,
        chunks_created=chunks_created if success else 0,
        message="Knowledge document indexed successfully" if success else "Failed to index document"
    )


@router.get(
    "/status",
    response_model=VectorDBStatusResponse,
    summary="Get RAG system status"
)
@limiter.limit(get_rate_limit_string())
async def rag_status(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """
    Get status of the RAG system components.

    Returns information about:
    - Vector database connection
    - Collections status
    - Embedding configuration
    """
    vector_db = get_vector_db()
    embedding_service = get_embedding_service()

    connected = vector_db.is_connected()

    products_info = None
    knowledge_info = None

    if connected:
        products_info = await vector_db.get_collection_info(
            settings.qdrant_collection_products
        )
        knowledge_info = await vector_db.get_collection_info(
            settings.qdrant_collection_knowledge
        )

    embedding_model = settings.embedding_model
    if settings.use_local_embeddings:
        embedding_model = settings.local_embedding_model

    return VectorDBStatusResponse(
        connected=connected,
        products_collection=products_info,
        knowledge_collection=knowledge_info,
        embedding_dimension=embedding_service.get_dimension(),
        embedding_model=embedding_model
    )


@router.post(
    "/embed",
    response_model=EmbedTextResponse,
    summary="Generate embedding for text"
)
@limiter.limit(get_rate_limit_string())
async def embed_text(
    request: Request,
    body: EmbedTextRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Generate an embedding vector for the given text.

    Useful for testing and debugging the embedding service.
    """
    embedding_service = get_embedding_service()
    embedding = await embedding_service.embed_text(body.text)

    model = settings.embedding_model
    if settings.use_local_embeddings:
        model = settings.local_embedding_model

    return EmbedTextResponse(
        embedding=embedding,
        dimension=len(embedding),
        model=model
    )
