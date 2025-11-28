"""
Products Tools for LangChain Agents
Wraps products service into LLM-compatible tools.
"""

import json
from typing import Dict, Any, Optional
from langchain.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from services import products
from database import async_session, Product
from sqlalchemy import select


@tool
async def search_products_tool(query: str, limit: int = 5) -> str:
    """
    Search for products using multilingual keyword matching.

    Args:
        query: Search query in Arabic, Franco-Arabic, or English (e.g., "جينز أزرق", "jeans azra2", "blue jeans")
        limit: Maximum number of products to return (default: 5)

    Returns:
        JSON string containing matching products with their details (name, price, sizes, colors, stock)

    Use this tool when the customer asks about:
    - Product availability ("Do you have hoodies?")
    - Product search ("Show me blue jeans")
    - General browsing ("What products do you sell?")
    """
    async with async_session() as db:
        try:
            result = await products.search_products(db=db, query=query, limit=limit)

            # Format for LLM consumption
            products_data = [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "sizes": p.sizes,
                    "colors": p.colors,
                    "stock": p.stock_count,
                    "description": p.description
                }
                for p in result.products
            ]

            return json.dumps({
                "success": True,
                "products": products_data,
                "total_found": result.search_metadata.total_found,
                "language_detected": result.search_metadata.detected_language
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


@tool
async def get_product_details_tool(product_id: str) -> str:
    """
    Get detailed information about a specific product by its ID.

    Args:
        product_id: The unique identifier of the product (UUID format)

    Returns:
        JSON string with complete product details including name, price, available sizes, colors, stock count, and description

    Use this when the customer asks about:
    - Specific product details ("Tell me more about product X")
    - Price of a specific item ("How much is product #123?")
    - Stock availability for a specific product
    """
    async with async_session() as db:
        try:
            stmt = select(Product).where(Product.id == product_id)
            result = await db.execute(stmt)
            product = result.scalar_one_or_none()

            if not product:
                return json.dumps({"success": False, "error": "Product not found"})

            return json.dumps({
                "success": True,
                "product": {
                    "id": str(product.id),
                    "name": product.name,
                    "price": product.price,
                    "sizes": product.sizes,
                    "colors": product.colors,
                    "stock_count": product.stock_count,
                    "description": product.description,
                    "is_active": product.is_active
                }
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


@tool
async def check_product_availability_tool(product_name: str, size: Optional[str] = None, color: Optional[str] = None) -> str:
    """
    Check if a product is available in stock, optionally filtered by size and color.

    Args:
        product_name: Name or description of the product to check
        size: Optional size filter (e.g., "M", "L", "XL")
        color: Optional color filter (e.g., "blue", "red", "أزرق")

    Returns:
        JSON string indicating availability status, stock count, and available variants

    Use this when the customer asks:
    - "Do you have size M in blue hoodies?"
    - "Is this product in stock?"
    - "What sizes are available?"
    """
    async with async_session() as db:
        try:
            # Search for the product first
            result = await products.search_products(db=db, query=product_name, limit=3)

            if not result.products:
                return json.dumps({
                    "success": False,
                    "available": False,
                    "message": f"No products found matching '{product_name}'"
                })

            # Check each product for availability
            available_products = []
            for product in result.products:
                # Check size availability
                size_available = True
                if size:
                    size_available = size.lower() in [s.lower() for s in (product.sizes or [])]

                # Check color availability
                color_available = True
                if color:
                    color_available = color.lower() in [c.lower() for c in (product.colors or [])]

                if size_available and color_available and product.stock_count > 0:
                    available_products.append({
                        "id": product.id,
                        "name": product.name,
                        "price": product.price,
                        "stock_count": product.stock_count,
                        "available_sizes": product.sizes,
                        "available_colors": product.colors
                    })

            return json.dumps({
                "success": True,
                "available": len(available_products) > 0,
                "products": available_products,
                "filters_applied": {
                    "size": size,
                    "color": color
                }
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
