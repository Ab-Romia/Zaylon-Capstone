"""
Order management service.
Handles order creation, customer management, and order history retrieval.
"""
import logging
import uuid
from typing import List, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import Order, Customer, Product
from models import (
    CreateOrderRequest, CreateOrderResponse,
    CustomerOrderHistory, EnhancedCustomerMetadata
)
from services.context import ensure_customer_exists, update_customer_profile
from core.enums import OrderStatus

logger = logging.getLogger(__name__)


async def create_order(
    db: AsyncSession,
    request: CreateOrderRequest
) -> CreateOrderResponse:
    """
    Create a new order in Supabase.

    This handles:
    1. Validating the product exists
    2. Ensuring customer exists in database
    3. Creating the order
    4. Updating customer profile with order info
    """
    try:
        # 1. Validate product exists
        try:
            product_uuid = uuid.UUID(request.product_id)
        except ValueError:
            return CreateOrderResponse(
                success=False,
                error="invalid_product_id",
                message=f"Invalid product ID format: {request.product_id}"
            )

        stmt = select(Product).where(Product.id == product_uuid)
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            return CreateOrderResponse(
                success=False,
                error="product_not_found",
                message=f"Product not found: {request.product_id}"
            )

        # Check stock
        if product.stock_count < request.quantity:
            return CreateOrderResponse(
                success=False,
                error="insufficient_stock",
                message=f"Not enough stock. Available: {product.stock_count}, Requested: {request.quantity}"
            )

        # Validate size and color (case-insensitive)
        available_sizes = [s.lower() for s in (product.sizes or [])]
        if request.size.lower() not in available_sizes:
            return CreateOrderResponse(
                success=False,
                error="invalid_size",
                message=f"Size '{request.size}' not available. Available sizes: {', '.join(product.sizes or [])}"
            )

        available_colors = [c.lower() for c in (product.colors or [])]
        if request.color.lower() not in available_colors:
            return CreateOrderResponse(
                success=False,
                error="invalid_color",
                message=f"Color '{request.color}' not available. Available colors: {', '.join(product.colors or [])}"
            )

        # 2. Ensure customer exists
        await ensure_customer_exists(db, request.customer_id)

        # Update customer profile with provided info
        await update_customer_profile(
            db,
            request.customer_id,
            name=request.customer_name,
            phone=request.phone
        )

        # 3. Create the order
        order = Order(
            product_id=product_uuid,
            product_name=request.product_name,
            size=request.size,
            color=request.color,
            quantity=request.quantity,
            total_price=request.total_price,
            customer_name=request.customer_name,
            customer_phone=request.phone,
            delivery_address=request.address,
            status=OrderStatus.PENDING.value,
            instagram_user=request.customer_id
        )

        db.add(order)

        # Update stock
        product.stock_count -= request.quantity

        await db.commit()
        await db.refresh(order)

        logger.info(f"Order created successfully: {order.id} for customer {request.customer_id}")

        return CreateOrderResponse(
            success=True,
            order_id=str(order.id),
            message=f"Order created successfully! Your order ID is {str(order.id)[:8].upper()}"
        )

    except Exception as e:
        logger.error(f"Failed to create order: {e}", exc_info=True)
        await db.rollback()
        return CreateOrderResponse(
            success=False,
            error="order_creation_failed",
            message=f"Failed to create order: {str(e)}"
        )


async def get_customer_order_history(
    db: AsyncSession,
    customer_id: str,
    limit: int = 5
) -> List[CustomerOrderHistory]:
    """
    Get customer's recent order history.
    """
    try:
        # Get orders for customer
        stmt = (
            select(Order)
            .where(Order.instagram_user == customer_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        orders = result.scalars().all()

        return [
            CustomerOrderHistory(
                order_id=str(order.id)[:8].upper(),
                product_name=order.product_name or "Unknown Product",
                total_price=float(order.total_price) if order.total_price else 0.0,
                status=order.status or "unknown",
                created_at=order.created_at.isoformat() if order.created_at else ""
            )
            for order in orders
        ]

    except Exception as e:
        logger.error(f"Failed to get order history: {e}")
        return []


async def get_enhanced_customer_metadata(
    db: AsyncSession,
    customer_id: str,
    base_metadata: Dict[str, Any]
) -> EnhancedCustomerMetadata:
    """
    Get enhanced customer metadata including order history.
    """
    try:
        # Get order statistics
        stmt = select(
            func.count(Order.id).label("total_orders"),
            func.sum(Order.total_price).label("total_spent"),
            func.max(Order.created_at).label("last_order")
        ).where(Order.instagram_user == customer_id)

        result = await db.execute(stmt)
        stats = result.first()

        # Get recent orders
        recent_orders = await get_customer_order_history(db, customer_id, limit=3)

        return EnhancedCustomerMetadata(
            name=base_metadata.get("name"),
            phone=base_metadata.get("phone"),
            total_interactions=base_metadata.get("total_interactions", 0),
            preferred_language=base_metadata.get("preferred_language", "en"),
            linked_channels=base_metadata.get("linked_channels", []),
            total_orders=stats.total_orders or 0,
            total_spent=float(stats.total_spent or 0),
            last_order_date=stats.last_order.isoformat() if stats.last_order else None,
            recent_orders=recent_orders
        )

    except Exception as e:
        logger.error(f"Failed to get enhanced metadata: {e}")
        return EnhancedCustomerMetadata(
            name=base_metadata.get("name"),
            phone=base_metadata.get("phone"),
            total_interactions=base_metadata.get("total_interactions", 0),
            preferred_language=base_metadata.get("preferred_language", "en"),
            linked_channels=base_metadata.get("linked_channels", []),
            total_orders=0,
            total_spent=0.0,
            last_order_date=None,
            recent_orders=[]
        )


def format_order_history_for_ai(orders: List[CustomerOrderHistory]) -> str:
    """
    Format customer order history for AI context.
    """
    if not orders:
        return "No previous orders."

    lines = ["CUSTOMER ORDER HISTORY:"]

    for order in orders:
        date = order.created_at[:10] if order.created_at else "Unknown"
        lines.append(f"- Order #{order.order_id}: {order.product_name} - {order.total_price:.2f} EGP ({order.status}) on {date}")

    return "\n".join(lines)
