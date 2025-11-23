"""n8n integration endpoints - main entry points for the workflow."""

import time
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from auth import verify_api_key, limiter, get_rate_limit_string
from models import (
    PrepareContextRequest, PrepareContextResponse,
    StoreInteractionRequest, StoreInteractionResponse,
    CreateOrderRequest, CreateOrderResponse,
    PrepareContextEnhancedRequest, PrepareContextEnhancedResponse
)
from services import products, context, intent, cache, analytics, get_rag_service
from services.orders import (
    create_order, get_customer_order_history,
    get_enhanced_customer_metadata, format_order_history_for_ai
)
from core.background import background_tasks
from core.enums import EventType

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/n8n", tags=["n8n Integration"])


@router.post(
    "/prepare-context",
    response_model=PrepareContextResponse,
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
        # Log cache hit in background
        background_tasks.add_task(
            analytics.log_event(
                db=db,
                customer_id=body.customer_id,
                event_type=EventType.CACHE_HIT,
                event_data={"message": body.message[:100]}
            )
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

    # Log product search in background
    background_tasks.add_task(
        analytics.log_event(
            db=db,
            customer_id=body.customer_id,
            event_type=EventType.PRODUCT_SEARCHED,
            event_data={
                "query": body.message[:100],
                "products_found": product_result.search_metadata.total_found
            }
        )
    )

    # 4. Classify intent
    intent_result = intent.classify_intent(body.message)

    # Log intent classification in background
    background_tasks.add_task(
        analytics.log_event(
            db=db,
            customer_id=body.customer_id,
            event_type=EventType.INTENT_CLASSIFIED,
            event_data={
                "intent": intent_result.intent,
                "confidence": intent_result.confidence
            }
        )
    )

    # 5. Determine if we should skip AI
    skip_ai = False
    cached_response = None

    if cache_result.cached:
        skip_ai = True
        cached_response = cache_result.response
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

    # Log message received in background
    background_tasks.add_task(
        analytics.log_event(
            db=db,
            customer_id=body.customer_id,
            event_type=EventType.MESSAGE_RECEIVED,
            event_data={
                "channel": body.channel,
                "intent": intent_result.intent,
                "skip_ai": skip_ai
            },
            response_time_ms=elapsed_ms
        )
    )

    return PrepareContextResponse(
        conversation_history=context_result.formatted_for_ai,
        relevant_products=product_result.formatted_for_ai,
        intent_analysis=intent_result,
        cached_response=cached_response,
        skip_ai=skip_ai,
        customer_metadata=context_result.customer_metadata
    )


@router.post(
    "/store-interaction",
    response_model=StoreInteractionResponse,
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
    if body.action not in ["create_order"]:
        await cache.store_cache(
            db=db,
            message=body.user_message,
            response=body.ai_response,
            intent=body.intent
        )

    # 3. Log analytics in background
    event_data = {
        "intent": body.intent,
        "action": body.action,
        "channel": body.channel
    }
    if body.order_data:
        event_data["order_data"] = body.order_data

    event_type = EventType.ORDER_CREATED if body.action == "create_order" else EventType.INTERACTION_COMPLETE

    background_tasks.add_task(
        analytics.log_event(
            db=db,
            customer_id=body.customer_id,
            event_type=event_type,
            event_data=event_data,
            response_time_ms=body.response_time_ms,
            ai_tokens_used=body.ai_tokens_used
        )
    )

    # Log cache miss if AI was called
    if body.ai_tokens_used:
        background_tasks.add_task(
            analytics.log_event(
                db=db,
                customer_id=body.customer_id,
                event_type=EventType.CACHE_MISS,
                event_data={"tokens_used": body.ai_tokens_used}
            )
        )

    logger.info(f"Stored interaction for {body.customer_id}, action={body.action}")

    return StoreInteractionResponse(success=True)


@router.post(
    "/create-order",
    response_model=CreateOrderResponse,
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

    # Log analytics in background
    if result.success:
        background_tasks.add_task(
            analytics.log_event(
                db=db,
                customer_id=body.customer_id,
                event_type=EventType.ORDER_CREATED,
                event_data={
                    "order_id": result.order_id,
                    "product_name": body.product_name,
                    "total_price": body.total_price,
                    "channel": body.channel
                }
            )
        )
    else:
        background_tasks.add_task(
            analytics.log_event(
                db=db,
                customer_id=body.customer_id,
                event_type=EventType.ORDER_FAILED,
                event_data={
                    "error": result.error,
                    "product_id": body.product_id
                }
            )
        )

    return result


@router.post(
    "/prepare-context-enhanced",
    response_model=PrepareContextEnhancedResponse,
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
    OPTIMIZED: Uses background tasks for analytics, streamlined DB queries.
    """
    start_time = time.time()

    # Classify intent first (CPU-bound, instant)
    intent_result = intent.classify_intent(body.message)

    # Check cache first (quick operation)
    cache_result = await cache.check_cache(db, body.message)

    # Retrieve context (single DB call with joins)
    context_result = await context.retrieve_context(
        db=db,
        customer_id=body.customer_id,
        limit=settings.max_conversation_history
    )

    # Get order history
    order_history = await get_customer_order_history(db, body.customer_id, limit=5)
    order_history_formatted = format_order_history_for_ai(order_history)

    # Get enhanced metadata
    base_meta = {
        "name": context_result.customer_metadata.name,
        "phone": context_result.customer_metadata.phone,
        "total_interactions": context_result.customer_metadata.total_interactions,
        "preferred_language": context_result.customer_metadata.preferred_language,
        "linked_channels": context_result.customer_metadata.linked_channels
    }
    enhanced_metadata = await get_enhanced_customer_metadata(db, body.customer_id, base_meta)

    # RAG search
    rag_service = get_rag_service()
    rag_context = await rag_service.prepare_rag_context(body.message, db)

    # Determine skip_ai
    skip_ai = False
    cached_response = None
    if cache_result.cached:
        skip_ai = True
        cached_response = cache_result.response
    elif intent_result.skip_ai and intent_result.suggested_response:
        skip_ai = True
        cached_response = intent_result.suggested_response

    # Store incoming message (must complete before response)
    await context.store_message(
        db=db,
        customer_id=body.customer_id,
        channel=body.channel,
        message=body.message,
        direction="incoming",
        intent=intent_result.intent
    )

    # Update customer profile if phone extracted
    if intent_result.entities.phone:
        await context.update_customer_profile(
            db=db,
            customer_id=body.customer_id,
            phone=intent_result.entities.phone
        )

    elapsed_ms = int((time.time() - start_time) * 1000)
    logger.info(f"Enhanced prepare context completed in {elapsed_ms}ms (skip_ai={skip_ai})")

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


# Combined request/response models for streamlined endpoint
class ProcessCompleteRequest(BaseModel):
    customer_id: str
    message: str
    channel: str = Field(..., pattern="^(instagram|whatsapp)$")
    ai_response: Optional[str] = None
    action: Optional[str] = None
    order_data: Optional[Dict[str, Any]] = None
    tokens_used: int = 0
    response_time_ms: int = 0


class ProcessCompleteResponse(BaseModel):
    # Context data (for AI call)
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
    # Order result (if order was created)
    order_created: bool = False
    order_id: Optional[str] = None
    order_error: Optional[str] = None
    final_response: Optional[str] = None


@router.post(
    "/process-complete",
    response_model=ProcessCompleteResponse,
    summary="Complete message processing in one call"
)
@limiter.limit(get_rate_limit_string())
async def n8n_process_complete(
    request: Request,
    body: ProcessCompleteRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Streamlined endpoint that handles everything in one call.

    Phase 1 (ai_response is None): Prepare context for AI
    Phase 2 (ai_response provided): Store interaction and create order if needed
    """
    start_time = time.time()

    # Phase 1: Prepare context
    if body.ai_response is None:
        # Check cache
        cache_result = await cache.check_cache(db, body.message)

        # Get context
        context_result = await context.retrieve_context(
            db=db, customer_id=body.customer_id, limit=settings.max_conversation_history
        )

        # Get order history
        order_history = await get_customer_order_history(db, body.customer_id, limit=5)
        order_history_formatted = format_order_history_for_ai(order_history)

        # Get enhanced metadata
        base_meta = {
            "name": context_result.customer_metadata.name,
            "phone": context_result.customer_metadata.phone,
            "total_interactions": context_result.customer_metadata.total_interactions,
            "preferred_language": context_result.customer_metadata.preferred_language,
            "linked_channels": context_result.customer_metadata.linked_channels
        }
        enhanced_metadata = await get_enhanced_customer_metadata(db, body.customer_id, base_meta)

        # RAG search
        rag_service = get_rag_service()
        rag_context = await rag_service.prepare_rag_context(body.message, db)

        # Classify intent
        intent_result = intent.classify_intent(body.message)

        # Determine skip_ai
        skip_ai = False
        cached_response = None
        if cache_result.cached:
            skip_ai = True
            cached_response = cache_result.response
        elif intent_result.skip_ai and intent_result.suggested_response:
            skip_ai = True
            cached_response = intent_result.suggested_response

        # Store incoming message
        await context.store_message(
            db=db, customer_id=body.customer_id, channel=body.channel,
            message=body.message, direction="incoming", intent=intent_result.intent
        )

        return ProcessCompleteResponse(
            conversation_history=context_result.formatted_for_ai,
            relevant_products=rag_context["products_formatted"],
            customer_order_history=order_history_formatted,
            intent=intent_result.intent,
            confidence=intent_result.confidence,
            entities=intent_result.entities.model_dump(),
            customer_name=enhanced_metadata.name,
            customer_phone=enhanced_metadata.phone,
            total_orders=enhanced_metadata.total_orders,
            total_spent=enhanced_metadata.total_spent,
            preferred_language=enhanced_metadata.preferred_language,
            skip_ai=skip_ai,
            cached_response=cached_response
        )

    # Phase 2: Process AI response
    else:
        final_response = body.ai_response
        order_created = False
        order_id = None
        order_error = None

        # Create order if requested
        if body.action == "create_order" and body.order_data:
            order_request = CreateOrderRequest(
                customer_id=body.customer_id,
                channel=body.channel,
                product_id=body.order_data.get("product_id", ""),
                product_name=body.order_data.get("product_name", ""),
                size=body.order_data.get("size", ""),
                color=body.order_data.get("color", ""),
                quantity=body.order_data.get("quantity", 1),
                total_price=body.order_data.get("total_price", 0),
                customer_name=body.order_data.get("customer_name", ""),
                phone=body.order_data.get("phone", ""),
                address=body.order_data.get("address", "")
            )

            order_result = await create_order(db, order_request)
            order_created = order_result.success
            order_id = order_result.order_id
            order_error = order_result.error

            # Replace placeholders
            if order_created:
                short_id = order_id[:8].upper() if order_id else ""
                final_response = final_response.replace("{{ORDER_ID}}", short_id)
            else:
                final_response = final_response.replace("{{ORDER_ID}}", "")
                final_response = final_response.replace("{{ERROR_MESSAGE}}", order_result.message or order_error or "")

        # Store interaction
        await context.store_message(
            db=db, customer_id=body.customer_id, channel=body.channel,
            message=final_response, direction="outgoing", intent=body.action
        )

        # Cache if appropriate
        if body.action not in ["create_order"]:
            await cache.store_cache(db, body.message, final_response, body.action or "answer")

        # Log analytics in background
        background_tasks.add_task(
            analytics.log_event(
                db=db, customer_id=body.customer_id,
                event_type=EventType.ORDER_CREATED if order_created else EventType.INTERACTION_COMPLETE,
                event_data={"action": body.action, "order_id": order_id},
                response_time_ms=body.response_time_ms,
                ai_tokens_used=body.tokens_used
            )
        )

        return ProcessCompleteResponse(
            conversation_history="",
            relevant_products="",
            customer_order_history="",
            intent=body.action or "answer",
            confidence=1.0,
            entities={},
            customer_name=None,
            customer_phone=None,
            total_orders=0,
            total_spent=0.0,
            preferred_language="en",
            skip_ai=False,
            cached_response=None,
            order_created=order_created,
            order_id=order_id,
            order_error=order_error,
            final_response=final_response
        )
