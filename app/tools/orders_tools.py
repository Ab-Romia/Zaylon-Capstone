"""
Orders Tools for LangChain Agents
Wraps order management service into LLM-compatible tools.
"""

import json
from typing import Optional
from langchain.tools import tool

from database import async_session
from models import CreateOrderRequest
from services.orders import create_order, get_customer_order_history
from core.enums import OrderStatus


@tool
async def create_order_tool(
    customer_id: str,
    product_id: str,
    product_name: str,
    size: str,
    color: str,
    quantity: int,
    total_price: float,
    customer_name: str,
    phone: str,
    address: str,
    channel: str = "instagram"
) -> str:
    """
    Create a new order for a customer.

    Args:
        customer_id: Customer identifier (e.g., "instagram:@username" or "whatsapp:+201234567890")
        product_id: The UUID of the product to order
        product_name: Name of the product
        size: Size selection (e.g., "M", "L", "XL")
        color: Color selection (e.g., "blue", "red", "أزرق")
        quantity: Number of items to order (must be >= 1)
        total_price: Total order price in EGP
        customer_name: Full name of the customer
        phone: Customer phone number (Egyptian format: +201234567890)
        address: Delivery address
        channel: Communication channel ("instagram" or "whatsapp", default: "instagram")

    Returns:
        JSON string with order creation result including order_id or error message

    Use this tool when the customer:
    - Wants to place an order ("I want to buy this hoodie")
    - Confirms their order details
    - Provides delivery information

    IMPORTANT: Only create an order after confirming:
    1. Product is in stock
    2. Size and color are valid
    3. Customer has provided: name, phone, and address
    """
    async with async_session() as db:
        try:
            request = CreateOrderRequest(
                customer_id=customer_id,
                channel=channel,
                product_id=product_id,
                product_name=product_name,
                size=size,
                color=color,
                quantity=quantity,
                total_price=total_price,
                customer_name=customer_name,
                phone=phone,
                address=address
            )

            result = await create_order(db, request)

            return json.dumps({
                "success": result.success,
                "order_id": result.order_id,
                "message": result.message,
                "error": result.error
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


@tool
async def get_order_history_tool(customer_id: str, limit: int = 5) -> str:
    """
    Retrieve a customer's order history.

    Args:
        customer_id: Customer identifier to lookup orders
        limit: Maximum number of recent orders to return (default: 5)

    Returns:
        JSON string containing list of past orders with details (order_id, product, price, status, date)

    Use this when the customer asks:
    - "What are my previous orders?"
    - "Show me my order history"
    - "When did I last order?"
    - For return/exchange requests (need to reference past orders)
    """
    async with async_session() as db:
        try:
            orders = await get_customer_order_history(db, customer_id, limit)

            orders_data = [
                {
                    "order_id": order.order_id,
                    "product_name": order.product_name,
                    "total_price": order.total_price,
                    "status": order.status,
                    "created_at": order.created_at
                }
                for order in orders
            ]

            return json.dumps({
                "success": True,
                "orders": orders_data,
                "total_orders": len(orders_data)
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


@tool
async def check_order_status_tool(customer_id: str, order_id: Optional[str] = None) -> str:
    """
    Check the status of a customer's order(s).

    Args:
        customer_id: Customer identifier
        order_id: Optional specific order ID to check (if None, returns latest order status)

    Returns:
        JSON string with order status information (pending, confirmed, shipped, delivered)

    Use this when the customer asks:
    - "Where is my order?"
    - "What's the status of my order?"
    - "Has my order shipped?"
    - "When will my order arrive?"
    """
    async with async_session() as db:
        try:
            orders = await get_customer_order_history(db, customer_id, limit=10)

            if not orders:
                return json.dumps({
                    "success": True,
                    "message": "No orders found for this customer"
                })

            # If specific order_id provided, find that order
            if order_id:
                matching_order = next((o for o in orders if o.order_id == order_id), None)
                if not matching_order:
                    return json.dumps({
                        "success": False,
                        "error": f"Order {order_id} not found"
                    })

                return json.dumps({
                    "success": True,
                    "order": {
                        "order_id": matching_order.order_id,
                        "product_name": matching_order.product_name,
                        "status": matching_order.status,
                        "created_at": matching_order.created_at
                    }
                }, ensure_ascii=False)

            # Return latest order if no specific order_id
            latest_order = orders[0]
            return json.dumps({
                "success": True,
                "latest_order": {
                    "order_id": latest_order.order_id,
                    "product_name": latest_order.product_name,
                    "status": latest_order.status,
                    "created_at": latest_order.created_at
                }
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
