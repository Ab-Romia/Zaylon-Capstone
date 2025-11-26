"""
RAG Tools for LangChain Agents
Wraps RAG service for semantic search and knowledge base queries.
"""

import json
from typing import Optional
from langchain.tools import tool

from database import get_db
from services import get_rag_service


@tool
async def search_knowledge_base_tool(query: str, limit: int = 3) -> str:
    """
    Search the knowledge base for FAQs, policies, and general information using semantic search.

    Args:
        query: Natural language question or search query (e.g., "What is your return policy?", "How do I track my order?")
        limit: Maximum number of relevant knowledge items to return (default: 3)

    Returns:
        JSON string containing relevant knowledge base articles with their content and similarity scores

    Use this tool when the customer asks:
    - General questions about policies ("What's your return policy?")
    - FAQ-type questions ("How long does shipping take?")
    - Information queries that aren't product-specific
    - Support questions ("How do I contact support?")

    IMPORTANT: This performs semantic search, so it works well with natural language questions.
    """
    try:
        rag_service = get_rag_service()

        # Search knowledge base
        knowledge_items = await rag_service.search_knowledge_base(query, limit=limit)

        if not knowledge_items:
            return json.dumps({
                "success": True,
                "found": False,
                "message": "No relevant information found in knowledge base",
                "suggestion": "Try rephrasing your question or use semantic product search"
            })

        # Format results
        results = [
            {
                "doc_id": item["doc_id"],
                "title": item.get("title", "Untitled"),
                "content": item["content"],
                "category": item.get("category", "general"),
                "similarity_score": item["similarity_score"]
            }
            for item in knowledge_items
        ]

        return json.dumps({
            "success": True,
            "found": True,
            "knowledge_items": results,
            "total_found": len(results)
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool
async def semantic_product_search_tool(query: str, limit: int = 5, retry_on_poor_results: bool = True) -> str:
    """
    Search for products using semantic/vector search for better understanding of customer intent.

    Args:
        query: Natural language product description or search query (e.g., "comfortable winter wear", "stylish blue outfit")
        limit: Maximum number of products to return (default: 5)
        retry_on_poor_results: If True, will automatically rewrite query and retry if first search yields poor results (default: True)

    Returns:
        JSON string with semantically matching products, including similarity scores

    Use this tool when:
    - Customer uses vague or descriptive language ("something warm and cozy")
    - Keyword search might fail ("outfit for cold weather")
    - You need better understanding of intent
    - Initial search yielded poor results (this tool has self-correction)

    SELF-CORRECTION FEATURE:
    If the first search returns results with low similarity scores (< 0.7),
    this tool will automatically rewrite the query and try again for better results.
    """
    async for db in get_db():
        try:
            rag_service = get_rag_service()

            # First attempt: Search with original query
            products = await rag_service.search_products_semantic(query, db, limit=limit)

            if not products:
                if retry_on_poor_results:
                    # Self-correction: Rewrite query and retry
                    # Extract keywords for retry
                    retry_query = _rewrite_query_for_retry(query)
                    products = await rag_service.search_products_semantic(retry_query, db, limit=limit)

                    if products:
                        return json.dumps({
                            "success": True,
                            "products": products,
                            "self_corrected": True,
                            "original_query": query,
                            "corrected_query": retry_query,
                            "message": "Initial search yielded poor results. Query was automatically rewritten."
                        }, ensure_ascii=False)

                return json.dumps({
                    "success": True,
                    "found": False,
                    "message": "No products found matching your description",
                    "suggestion": "Try using more specific keywords or product categories"
                })

            # Check if results have low similarity (< 0.7)
            avg_similarity = sum(p.get("similarity_score", 0) for p in products) / len(products)

            if avg_similarity < 0.7 and retry_on_poor_results:
                # Self-correction triggered
                retry_query = _rewrite_query_for_retry(query)
                retry_products = await rag_service.search_products_semantic(retry_query, db, limit=limit)

                # Use retry results if they're better
                if retry_products:
                    retry_avg_similarity = sum(p.get("similarity_score", 0) for p in retry_products) / len(retry_products)
                    if retry_avg_similarity > avg_similarity:
                        return json.dumps({
                            "success": True,
                            "products": retry_products,
                            "self_corrected": True,
                            "original_query": query,
                            "corrected_query": retry_query,
                            "similarity_improvement": retry_avg_similarity - avg_similarity
                        }, ensure_ascii=False)

            return json.dumps({
                "success": True,
                "found": True,
                "products": products,
                "self_corrected": False,
                "average_similarity": avg_similarity
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


def _rewrite_query_for_retry(original_query: str) -> str:
    """
    Internal helper to rewrite a query for better semantic search results.

    Strategy:
    1. Extract key nouns and adjectives
    2. Add category hints
    3. Simplify language
    """
    # Simple keyword extraction (in production, could use NLP)
    keywords = []

    # Common product categories
    if "winter" in original_query.lower() or "cold" in original_query.lower():
        keywords.append("hoodie jacket sweater")
    if "summer" in original_query.lower() or "warm" in original_query.lower():
        keywords.append("t-shirt shorts")
    if "comfortable" in original_query.lower() or "cozy" in original_query.lower():
        keywords.append("soft cotton")
    if "stylish" in original_query.lower() or "trendy" in original_query.lower():
        keywords.append("fashion modern")

    # Extract color words
    colors = ["blue", "red", "black", "white", "green", "yellow", "أزرق", "أحمر", "أسود", "أبيض"]
    for color in colors:
        if color in original_query.lower():
            keywords.append(color)

    # Extract garment types
    garments = ["hoodie", "jeans", "shirt", "pants", "jacket", "dress", "هودي", "جينز", "شيرت"]
    for garment in garments:
        if garment in original_query.lower():
            keywords.append(garment)

    if keywords:
        return " ".join(keywords)

    # Fallback: return simplified version
    return " ".join(original_query.split()[:3])
