"""Intent classification endpoint."""

import logging

from fastapi import APIRouter, Depends, Request

from app.core.security import verify_api_key, limiter, get_rate_limit_string
from app.schemas import IntentClassifyRequest, IntentClassifyResponse
from app.services import intent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intent", tags=["Intent"])


@router.post(
    "/classify",
    response_model=IntentClassifyResponse,
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
