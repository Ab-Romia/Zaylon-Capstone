"""Analytics schemas."""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


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
