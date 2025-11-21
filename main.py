"""
E-commerce DM Microservice - FastAPI Application
Main entry point with all routes and application setup.
"""
import time
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db, init_db, close_db, Product
from auth import verify_api_key, limiter, get_rate_limit_string
from models import (
    # Product models
    ProductSearchRequest, ProductSearchResponse,
    # Context models
    StoreContextRequest, StoreContextResponse,
    RetrieveContextResponse, LinkChannelsRequest, LinkChannelsResponse,
    # Intent models
    IntentClassifyRequest, IntentClassifyResponse,
    # Cache models
    CacheCheckRequest, CacheCheckResponse, CacheStoreRequest, CacheStoreResponse,
    # Analytics models
    AnalyticsLogRequest, AnalyticsLogResponse, AnalyticsDashboardResponse,
    # n8n integration models
    PrepareContextRequest, PrepareContextResponse,
    StoreInteractionRequest, StoreInteractionResponse,
    # RAG models
    IndexProductRequest, IndexProductResponse, IndexAllProductsResponse,
    IndexKnowledgeRequest, IndexKnowledgeResponse,
    RAGSearchRequest, RAGSearchResponse, RAGProductResult, RAGKnowledgeResult,
    VectorDBStatusResponse, EmbedTextRequest, EmbedTextResponse,
    PrepareContextResponseRAG,
    # Order management models
    CreateOrderRequest, CreateOrderResponse,
    PrepareContextEnhancedRequest, PrepareContextEnhancedResponse,
    # Common models
    HealthCheckResponse, ErrorResponse
)
from services import products, context, intent, cache, analytics
from services import (
    get_embedding_service, get_vector_db, init_vector_db, close_vector_db,
    get_ingestion_service, get_rag_service
)
from services.orders import (
    create_order, get_customer_order_history,
    get_enhanced_customer_metadata, format_order_history_for_ai
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting E-commerce DM Microservice with RAG support...")
    await init_db()
    logger.info("Database initialized")

    # Initialize RAG system
    try:
        embedding_service = get_embedding_service()
        embedding_dim = embedding_service.get_dimension()
        logger.info(f"Embedding service initialized (dimension: {embedding_dim})")

        vector_db = get_vector_db()
        if vector_db.is_connected():
            await init_vector_db(embedding_dim)
            logger.info("Vector database (Qdrant) initialized")
        else:
            logger.warning("Vector database not connected - RAG features will be limited")
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}")
        logger.warning("Service will continue without RAG features")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await close_db()
    await close_vector_db()
    logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered microservice for e-commerce Instagram/WhatsApp DM automation",
    lifespan=lifespan
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=str(exc.detail),
            timestamp=datetime.utcnow().isoformat()
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc) if settings.debug else "An unexpected error occurred",
            timestamp=datetime.utcnow().isoformat()
        ).model_dump()
    )


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check service health and database connectivity."""
    try:
        # Test database connection
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"

    # Check Qdrant status
    qdrant_status = "not_configured"
    try:
        vector_db = get_vector_db()
        if vector_db.is_connected():
            qdrant_status = "connected"
        else:
            qdrant_status = "disconnected"
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        qdrant_status = "error"

    overall_status = "healthy" if db_status == "connected" else "degraded"
    if qdrant_status == "disconnected":
        overall_status = "degraded"

    return HealthCheckResponse(
        status=overall_status,
        version=settings.app_version,
        database=db_status,
        qdrant=qdrant_status,
        timestamp=datetime.utcnow().isoformat()
    )


# ============================================================================
# Product Search Endpoints
# ============================================================================

@app.post(
    "/products/search",
    response_model=ProductSearchResponse,
    tags=["Products"],
    summary="Search products with multilingual support"
)
@limiter.limit(get_rate_limit_string())
async def search_products(
    request: Request,
    body: ProductSearchRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Search products using multilingual keyword matching.

    Supports:
    - Arabic: جينز, بنطلون, هودي, شيرت
    - Franco-Arabic: jeans, pants, 7ezaa2, azra2
    - English: jeans, pants, hoodie, shirt

    Returns relevant products formatted for AI context injection.
    """
    start_time = time.time()

    result = await products.search_products(
        db=db,
        query=body.query,
        limit=body.limit
    )

    elapsed_ms = int((time.time() - start_time) * 1000)
    logger.info(f"Product search completed in {elapsed_ms}ms")

    return result


# ============================================================================
# Conversation Context Endpoints
# ============================================================================

@app.post(
    "/context/store",
    response_model=StoreContextResponse,
    tags=["Context"],
    summary="Store conversation message"
)
@limiter.limit(get_rate_limit_string())
async def store_context(
    request: Request,
    body: StoreContextRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Store a conversation message with metadata."""
    return await context.store_message(
        db=db,
        customer_id=body.customer_id,
        channel=body.channel,
        message=body.message,
        direction=body.direction,
        intent=body.intent,
        metadata=body.metadata
    )


@app.get(
    "/context/retrieve",
    response_model=RetrieveContextResponse,
    tags=["Context"],
    summary="Retrieve conversation history"
)
@limiter.limit(get_rate_limit_string())
async def retrieve_context(
    request: Request,
    customer_id: str = Query(..., description="Customer identifier"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of messages to retrieve"),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Retrieve conversation history and customer metadata.

    Automatically handles cross-channel linking (Instagram + WhatsApp).
    Returns formatted history ready for AI prompt injection.
    """
    return await context.retrieve_context(
        db=db,
        customer_id=customer_id,
        limit=limit
    )


@app.post(
    "/context/link-channels",
    response_model=LinkChannelsResponse,
    tags=["Context"],
    summary="Link customer channels"
)
@limiter.limit(get_rate_limit_string())
async def link_channels(
    request: Request,
    body: LinkChannelsRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Link two channel IDs as belonging to the same customer.

    Example: Link instagram:@user with whatsapp:+201234567890
    """
    return await context.link_channels(
        db=db,
        primary_id=body.primary_id,
        secondary_id=body.secondary_id
    )


# ============================================================================
# Intent Classification Endpoints
# ============================================================================

@app.post(
    "/intent/classify",
    response_model=IntentClassifyResponse,
    tags=["Intent"],
    summary="Classify message intent"
)
@limiter.limit(get_rate_limit_string())
async def classify_intent(
    request: Request,
    body: IntentClassifyRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Classify the intent of a message using rule-based patterns.

    Supported intents:
    - greeting, thanks, goodbye
    - price_inquiry, order_intent, availability_check
    - variant_inquiry, order_status, complaint
    - general_inquiry (fallback)

    Also extracts entities: product_name, size, color, quantity, phone
    """
    return intent.classify_intent(
        message=body.message,
        context=body.context
    )


# ============================================================================
# Response Cache Endpoints
# ============================================================================

@app.post(
    "/cache/check",
    response_model=CacheCheckResponse,
    tags=["Cache"],
    summary="Check for cached response"
)
@limiter.limit(get_rate_limit_string())
async def check_cache(
    request: Request,
    body: CacheCheckRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Check if a cached response exists for the message.

    Normalizes message and checks against cache.
    Returns saved tokens estimate if cache hit.
    """
    return await cache.check_cache(
        db=db,
        message=body.message,
        max_age_hours=body.max_age_hours
    )


@app.post(
    "/cache/store",
    response_model=CacheStoreResponse,
    tags=["Cache"],
    summary="Store response in cache"
)
@limiter.limit(get_rate_limit_string())
async def store_cache(
    request: Request,
    body: CacheStoreRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Store a response in cache with TTL.

    Automatically skips personalized responses (order confirmations, etc.).
    """
    return await cache.store_cache(
        db=db,
        message=body.message,
        response=body.response,
        intent=body.intent,
        ttl_hours=body.ttl_hours
    )


# ============================================================================
# Analytics Endpoints
# ============================================================================

@app.post(
    "/analytics/log",
    response_model=AnalyticsLogResponse,
    tags=["Analytics"],
    summary="Log analytics event"
)
@limiter.limit(get_rate_limit_string())
async def log_analytics(
    request: Request,
    body: AnalyticsLogRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Log an analytics event.

    Event types: message_received, intent_classified, cache_hit,
    cache_miss, order_created, product_searched, etc.
    """
    return await analytics.log_event(
        db=db,
        customer_id=body.customer_id,
        event_type=body.event_type,
        event_data=body.event_data,
        response_time_ms=body.response_time_ms,
        ai_tokens_used=body.ai_tokens_used
    )


@app.get(
    "/analytics/dashboard",
    response_model=AnalyticsDashboardResponse,
    tags=["Analytics"],
    summary="Get analytics dashboard"
)
@limiter.limit(get_rate_limit_string())
async def get_dashboard(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get analytics dashboard with key metrics.

    Includes: total messages, orders, conversion rate, response times,
    top intents, popular products, AI cost estimate, cache hit rate.
    """
    # Parse dates
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None

    return await analytics.get_dashboard(
        db=db,
        start_date=start_dt,
        end_date=end_dt
    )


# ============================================================================
# n8n Integration Endpoints (Main Entry Points)
# ============================================================================

@app.post(
    "/n8n/prepare-context",
    response_model=PrepareContextResponse,
    tags=["n8n Integration"],
    summary="Prepare full context for AI (n8n main entry point)"
)
@limiter.limit(get_rate_limit_string())
async def n8n_prepare_context(
    request: Request,
    body: PrepareContextRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Main n8n integration endpoint.

    This endpoint does everything in one call:
    1. Check cache for existing response
    2. Retrieve conversation history
    3. Search relevant products
    4. Classify intent and extract entities
    5. Return everything formatted and ready for AI

    If skip_ai is True, use cached_response directly without calling OpenAI.
    """
    start_time = time.time()

    # 1. Check cache first
    cache_result = await cache.check_cache(db, body.message)
    if cache_result.cached:
        # Log cache hit
        await analytics.log_event(
            db=db,
            customer_id=body.customer_id,
            event_type="cache_hit",
            event_data={"message": body.message[:100]}
        )

    # 2. Retrieve conversation history
    context_result = await context.retrieve_context(
        db=db,
        customer_id=body.customer_id,
        limit=settings.max_conversation_history
    )

    # 3. Search relevant products
    product_result = await products.search_products(
        db=db,
        query=body.message,
        limit=settings.max_product_search_results
    )

    # Log product search
    await analytics.log_event(
        db=db,
        customer_id=body.customer_id,
        event_type="product_searched",
        event_data={
            "query": body.message[:100],
            "products_found": product_result.search_metadata.total_found
        }
    )

    # 4. Classify intent
    intent_result = intent.classify_intent(body.message)

    # Log intent classification
    await analytics.log_event(
        db=db,
        customer_id=body.customer_id,
        event_type="intent_classified",
        event_data={
            "intent": intent_result.intent,
            "confidence": intent_result.confidence
        }
    )

    # 5. Determine if we should skip AI
    skip_ai = False
    cached_response = None

    # Check if cache hit
    if cache_result.cached:
        skip_ai = True
        cached_response = cache_result.response
    # Check if intent-based skip
    elif intent_result.skip_ai and intent_result.suggested_response:
        skip_ai = True
        cached_response = intent_result.suggested_response

    # 6. Store incoming message
    await context.store_message(
        db=db,
        customer_id=body.customer_id,
        channel=body.channel,
        message=body.message,
        direction="incoming",
        intent=intent_result.intent
    )

    # Update customer profile with extracted entities
    if intent_result.entities.phone:
        await context.update_customer_profile(
            db=db,
            customer_id=body.customer_id,
            phone=intent_result.entities.phone
        )

    elapsed_ms = int((time.time() - start_time) * 1000)
    logger.info(f"Prepare context completed in {elapsed_ms}ms (skip_ai={skip_ai})")

    # Log message received
    await analytics.log_event(
        db=db,
        customer_id=body.customer_id,
        event_type="message_received",
        event_data={
            "channel": body.channel,
            "intent": intent_result.intent,
            "skip_ai": skip_ai
        },
        response_time_ms=elapsed_ms
    )

    return PrepareContextResponse(
        conversation_history=context_result.formatted_for_ai,
        relevant_products=product_result.formatted_for_ai,
        intent_analysis=intent_result,
        cached_response=cached_response,
        skip_ai=skip_ai,
        customer_metadata=context_result.customer_metadata
    )


@app.post(
    "/n8n/store-interaction",
    response_model=StoreInteractionResponse,
    tags=["n8n Integration"],
    summary="Store complete interaction (n8n after AI response)"
)
@limiter.limit(get_rate_limit_string())
async def n8n_store_interaction(
    request: Request,
    body: StoreInteractionRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Store complete interaction after AI response.

    This endpoint:
    1. Stores outgoing response in conversation history
    2. Caches the response if appropriate
    3. Logs analytics event with response time and tokens
    4. Updates customer metadata if new info extracted

    Call this after n8n receives AI response.
    """
    # 1. Store outgoing message
    await context.store_message(
        db=db,
        customer_id=body.customer_id,
        channel=body.channel,
        message=body.ai_response,
        direction="outgoing",
        intent=body.intent,
        metadata={
            "action": body.action,
            "order_data": body.order_data
        }
    )

    # 2. Cache the response (if appropriate)
    if body.action not in ["create_order"]:  # Don't cache order confirmations
        await cache.store_cache(
            db=db,
            message=body.user_message,
            response=body.ai_response,
            intent=body.intent
        )

    # 3. Log analytics
    event_data = {
        "intent": body.intent,
        "action": body.action,
        "channel": body.channel
    }
    if body.order_data:
        event_data["order_data"] = body.order_data

    await analytics.log_event(
        db=db,
        customer_id=body.customer_id,
        event_type="interaction_complete" if body.action != "create_order" else "order_created",
        event_data=event_data,
        response_time_ms=body.response_time_ms,
        ai_tokens_used=body.ai_tokens_used
    )

    # Log cache miss (since AI was called)
    if body.ai_tokens_used:
        await analytics.log_event(
            db=db,
            customer_id=body.customer_id,
            event_type="cache_miss",
            event_data={"tokens_used": body.ai_tokens_used}
        )

    logger.info(f"Stored interaction for {body.customer_id}, action={body.action}")

    return StoreInteractionResponse(success=True)


@app.post(
    "/n8n/create-order",
    response_model=CreateOrderResponse,
    tags=["n8n Integration"],
    summary="Create order through microservice"
)
@limiter.limit(get_rate_limit_string())
async def n8n_create_order(
    request: Request,
    body: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Create an order through the microservice.

    This endpoint handles:
    1. Validates product exists and has stock
    2. Ensures customer exists in database
    3. Creates the order
    4. Updates customer profile
    5. Returns order_id or error message

    The AI should use order_id in success response or error in failure response.
    """
    result = await create_order(db, body)

    # Log analytics
    if result.success:
        await analytics.log_event(
            db=db,
            customer_id=body.customer_id,
            event_type="order_created",
            event_data={
                "order_id": result.order_id,
                "product_name": body.product_name,
                "total_price": body.total_price,
                "channel": body.channel
            }
        )
    else:
        await analytics.log_event(
            db=db,
            customer_id=body.customer_id,
            event_type="order_failed",
            event_data={
                "error": result.error,
                "product_id": body.product_id
            }
        )

    return result


@app.post(
    "/n8n/prepare-context-enhanced",
    response_model=PrepareContextEnhancedResponse,
    tags=["n8n Integration"],
    summary="Prepare enhanced context with customer order history"
)
@limiter.limit(get_rate_limit_string())
async def n8n_prepare_context_enhanced(
    request: Request,
    body: PrepareContextEnhancedRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Enhanced context preparation with customer order history.

    This endpoint does everything in one call:
    1. Check cache for existing response
    2. Retrieve conversation history
    3. Get customer's previous orders
    4. Search relevant products (hybrid RAG)
    5. Classify intent and extract entities
    6. Return everything formatted and ready for AI

    Includes customer order history for personalized responses.
    """
    start_time = time.time()

    # 1. Check cache first
    cache_result = await cache.check_cache(db, body.message)
    if cache_result.cached:
        await analytics.log_event(
            db=db,
            customer_id=body.customer_id,
            event_type="cache_hit",
            event_data={"message": body.message[:100]}
        )

    # 2. Retrieve conversation history
    context_result = await context.retrieve_context(
        db=db,
        customer_id=body.customer_id,
        limit=settings.max_conversation_history
    )

    # 3. Get customer order history
    order_history = await get_customer_order_history(db, body.customer_id, limit=5)
    order_history_formatted = format_order_history_for_ai(order_history)

    # 4. Get enhanced customer metadata
    base_meta = {
        "name": context_result.customer_metadata.name,
        "phone": context_result.customer_metadata.phone,
        "total_interactions": context_result.customer_metadata.total_interactions,
        "preferred_language": context_result.customer_metadata.preferred_language,
        "linked_channels": context_result.customer_metadata.linked_channels
    }
    enhanced_metadata = await get_enhanced_customer_metadata(db, body.customer_id, base_meta)

    # 5. Search relevant products using RAG
    rag_service = get_rag_service()
    rag_context = await rag_service.prepare_rag_context(body.message, db)

    # Log product search
    await analytics.log_event(
        db=db,
        customer_id=body.customer_id,
        event_type="product_searched",
        event_data={
            "query": body.message[:100],
            "products_found": len(rag_context["products"])
        }
    )

    # 6. Classify intent
    intent_result = intent.classify_intent(body.message)

    await analytics.log_event(
        db=db,
        customer_id=body.customer_id,
        event_type="intent_classified",
        event_data={
            "intent": intent_result.intent,
            "confidence": intent_result.confidence
        }
    )

    # 7. Determine if we should skip AI
    skip_ai = False
    cached_response = None

    if cache_result.cached:
        skip_ai = True
        cached_response = cache_result.response
    elif intent_result.skip_ai and intent_result.suggested_response:
        skip_ai = True
        cached_response = intent_result.suggested_response

    # 8. Store incoming message
    await context.store_message(
        db=db,
        customer_id=body.customer_id,
        channel=body.channel,
        message=body.message,
        direction="incoming",
        intent=intent_result.intent
    )

    # Update customer profile with extracted entities
    if intent_result.entities.phone:
        await context.update_customer_profile(
            db=db,
            customer_id=body.customer_id,
            phone=intent_result.entities.phone
        )

    elapsed_ms = int((time.time() - start_time) * 1000)
    logger.info(f"Enhanced prepare context completed in {elapsed_ms}ms (skip_ai={skip_ai})")

    await analytics.log_event(
        db=db,
        customer_id=body.customer_id,
        event_type="message_received",
        event_data={
            "channel": body.channel,
            "intent": intent_result.intent,
            "skip_ai": skip_ai,
            "total_orders": enhanced_metadata.total_orders
        },
        response_time_ms=elapsed_ms
    )

    return PrepareContextEnhancedResponse(
        conversation_history=context_result.formatted_for_ai,
        relevant_products=rag_context["products_formatted"],
        intent_analysis=intent_result,
        cached_response=cached_response,
        skip_ai=skip_ai,
        customer_metadata=enhanced_metadata,
        customer_order_history=order_history_formatted,
        rag_enabled=True
    )


# ============================================================================
# RAG System Endpoints
# ============================================================================

@app.post(
    "/rag/search",
    response_model=RAGSearchResponse,
    tags=["RAG System"],
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
        products = await rag_service.search_products_semantic(
            body.query, db, limit=body.limit
        )
        knowledge_items = []
        if body.include_knowledge:
            knowledge_items = await rag_service.search_knowledge_base(
                body.query, limit=3
            )

        products_formatted = rag_service.format_products_for_ai(products)
        knowledge_formatted = rag_service.format_knowledge_for_ai(knowledge_items)

        return RAGSearchResponse(
            products=[RAGProductResult(**p) for p in products],
            products_formatted=products_formatted,
            knowledge_items=[RAGKnowledgeResult(**k) for k in knowledge_items],
            knowledge_formatted=knowledge_formatted,
            metadata={
                "search_method": "semantic",
                "total_found": len(products)
            },
            rag_enabled=True
        )

    elif body.search_method == "keyword":
        # Keyword search only
        products = await rag_service.search_products_keyword(
            body.query, db, limit=body.limit
        )

        products_formatted = rag_service.format_products_for_ai(products)

        return RAGSearchResponse(
            products=[RAGProductResult(**p) for p in products],
            products_formatted=products_formatted,
            knowledge_items=[],
            knowledge_formatted="",
            metadata={
                "search_method": "keyword",
                "total_found": len(products)
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


@app.post(
    "/rag/index/product",
    response_model=IndexProductResponse,
    tags=["RAG System"],
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


@app.post(
    "/rag/index/products/all",
    response_model=IndexAllProductsResponse,
    tags=["RAG System"],
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


@app.post(
    "/rag/index/knowledge",
    response_model=IndexKnowledgeResponse,
    tags=["RAG System"],
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


@app.get(
    "/rag/status",
    response_model=VectorDBStatusResponse,
    tags=["RAG System"],
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


@app.post(
    "/rag/embed",
    response_model=EmbedTextResponse,
    tags=["RAG System"],
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


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        workers=1
    )
