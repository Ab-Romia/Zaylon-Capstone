"""Order management schemas."""
from typing import Optional, List
from pydantic import BaseModel, Field
from .context import CustomerMetadata


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


class EnhancedCustomerMetadata(CustomerMetadata):
    """Enhanced customer metadata including order history."""
    total_orders: int = 0
    total_spent: float = 0.0
    last_order_date: Optional[str] = None
    recent_orders: List[CustomerOrderHistory] = []
