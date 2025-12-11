"""
Multilingual product search service (RAG-lite).
PHASE 2: Enhanced with semantic + keyword hybrid search.
"""
import re
from typing import List, Tuple, Set, Optional
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Product
from app.schemas import ProductInfo, SearchMetadata, ProductSearchResponse
from app.search.hybrid import get_hybrid_search_engine
from app.search.multilingual import detect_language as detect_lang_v2
import logging

logger = logging.getLogger(__name__)

# Multilingual keyword dictionaries
PRODUCT_KEYWORDS = {
    # Clothing items - mapped to English search terms
    "jeans": ["jeans", "جينز", "جينس", "jeanz", "denim"],
    "pants": ["pants", "بنطلون", "بنطلونات", "pantalon", "bantalon", "trousers"],
    "hoodie": ["hoodie", "هودي", "هوديز", "hoody", "sweatshirt"],
    "shirt": ["shirt", "شيرت", "قميص", "shert", "t-shirt", "tshirt", "tee"],
    "jacket": ["jacket", "جاكيت", "جاكت", "jaket", "coat"],
    "shoes": ["shoes", "حذاء", "جزمة", "shoe", "7ezaa2", "gizma", "sneakers"],
    "dress": ["dress", "فستان", "fostan", "dresses"],
    "skirt": ["skirt", "جيبة", "jiba", "skirts"],
    "shorts": ["shorts", "شورت", "short"],
    "sweater": ["sweater", "سويتر", "pullover"],
    "bag": ["bag", "شنطة", "حقيبة", "shanta", "bags"],
    "cap": ["cap", "كاب", "طاقية", "hat"],
}

# Color mappings
COLOR_KEYWORDS = {
    "black": ["black", "اسود", "أسود", "eswed", "aswad"],
    "white": ["white", "ابيض", "أبيض", "abyad", "abyed"],
    "red": ["red", "احمر", "أحمر", "a7mar", "ahmar"],
    "blue": ["blue", "ازرق", "أزرق", "azra2", "azraq"],
    "green": ["green", "اخضر", "أخضر", "akhdar", "a5dar"],
    "yellow": ["yellow", "اصفر", "أصفر", "asfar"],
    "brown": ["brown", "بني", "bonny", "bunni"],
    "gray": ["gray", "grey", "رمادي", "رصاصي", "grey", "rasasi"],
    "pink": ["pink", "وردي", "زهري", "wardy", "baby"],
    "orange": ["orange", "برتقالي", "borto2aly"],
    "navy": ["navy", "كحلي", "كحل", "ka7ly"],
    "beige": ["beige", "بيج", "بيچ"],
}

# Size patterns
SIZE_PATTERNS = [
    r'\b(xs|s|m|l|xl|xxl|xxxl)\b',
    r'\b(\d{2})\b',  # Numeric sizes like 32, 34, etc.
    r'\b(small|medium|large)\b',
    r'\b(صغير|وسط|كبير)\b',  # Arabic sizes
]


def detect_language(text: str) -> str:
    """Detect language of the input text."""
    arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
    total_chars = len(re.findall(r'[a-zA-Z\u0600-\u06FF]', text))

    if total_chars == 0:
        return "en"

    arabic_ratio = arabic_chars / total_chars

    if arabic_ratio > 0.5:
        return "ar"
    elif arabic_ratio > 0:
        return "franco-arabic"
    else:
        return "en"


def extract_product_keywords(query: str) -> Tuple[Set[str], Set[str]]:
    """Extract product type and color keywords from query in any language."""
    query_lower = query.lower()
    query_words = set(re.findall(r'[\w\u0600-\u06FF]+', query_lower))

    matched_products = set()
    matched_colors = set()

    # Find product types
    for product_key, variants in PRODUCT_KEYWORDS.items():
        for variant in variants:
            if variant.lower() in query_lower or variant.lower() in query_words:
                matched_products.add(product_key)
                break

    # Find colors
    for color_key, variants in COLOR_KEYWORDS.items():
        for variant in variants:
            if variant.lower() in query_lower or variant.lower() in query_words:
                matched_colors.add(color_key)
                break

    return matched_products, matched_colors


def extract_size(query: str) -> str | None:
    """Extract size from query."""
    query_lower = query.lower()

    for pattern in SIZE_PATTERNS:
        match = re.search(pattern, query_lower, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    return None


async def search_products(
    db: AsyncSession,
    query: str,
    limit: int = 3,
    use_hybrid: bool = True
) -> ProductSearchResponse:
    """
    Search products using semantic + keyword hybrid search (Phase 2).

    This is an enhanced RAG approach:
    1. Detect language (7 languages supported)
    2. Enhance query with multilingual synonyms
    3. Perform semantic search (Qdrant vectors) + keyword search (PostgreSQL FTS)
    4. Combine and rank results
    5. Return formatted results for AI context

    Args:
        db: Database session
        query: Search query in any language
        limit: Maximum number of results
        use_hybrid: If True, use hybrid search (default). If False, fallback to keyword-only

    Returns:
        ProductSearchResponse with products and metadata
    """
    logger.info(f"Searching products with query: '{query}' (hybrid: {use_hybrid})")

    # Detect language using improved multilingual module
    detected_language = detect_lang_v2(query)

    try:
        if use_hybrid:
            # PHASE 2: Use hybrid semantic + keyword search
            hybrid_engine = get_hybrid_search_engine()

            # Perform hybrid search
            hybrid_results = await hybrid_engine.search(
                query=query,
                db_session=db,
                limit=limit
            )

            # Convert hybrid results to Product objects
            product_list = []
            matched_keywords = set()

            for result in hybrid_results:
                # Extract product info from payload
                product_info = ProductInfo(
                    id=result.payload.get("id", result.id),
                    name=result.payload.get("name", ""),
                    price=float(result.payload.get("price", 0)),
                    sizes=result.payload.get("sizes", []),
                    colors=result.payload.get("colors", []),
                    stock_count=result.payload.get("stock_count", 0),
                    description=result.payload.get("description", "")
                )
                product_list.append(product_info)

                # Track matched fields for metadata
                matched_keywords.update(result.matched_fields)

            logger.info(
                f"Hybrid search returned {len(product_list)} results "
                f"(semantic: {sum(1 for r in hybrid_results if r.source in ['semantic', 'both'])}, "
                f"keyword: {sum(1 for r in hybrid_results if r.source in ['keyword', 'both'])})"
            )

        else:
            # Fallback to keyword-only search (old implementation)
            logger.info("Using fallback keyword-only search")
            product_list, matched_keywords = await _keyword_only_search(db, query, limit)

    except Exception as e:
        logger.error(f"Hybrid search failed, falling back to keyword search: {str(e)}", exc_info=True)
        product_list, matched_keywords = await _keyword_only_search(db, query, limit)

    # Format for AI context
    formatted_for_ai = format_products_for_ai(product_list)

    return ProductSearchResponse(
        products=product_list,
        formatted_for_ai=formatted_for_ai,
        search_metadata=SearchMetadata(
            detected_language=detected_language,
            matched_keywords=list(matched_keywords),
            total_found=len(product_list)
        )
    )


async def _keyword_only_search(
    db: AsyncSession,
    query: str,
    limit: int
) -> Tuple[List[ProductInfo], Set[str]]:
    """
    Fallback keyword-only search (original implementation).
    Used when hybrid search fails or is disabled.
    """
    # Detect language
    detected_language = detect_language(query)

    # Extract keywords
    product_keywords, color_keywords = extract_product_keywords(query)
    size = extract_size(query)

    all_keywords = list(product_keywords) + list(color_keywords)
    if size:
        all_keywords.append(size)

    logger.info(f"Keyword search - language: {detected_language}, keywords: {all_keywords}")

    # Build database query
    conditions = []

    # Add product keyword conditions
    for keyword in product_keywords:
        conditions.append(Product.name.ilike(f"%{keyword}%"))
        conditions.append(Product.description.ilike(f"%{keyword}%"))

    # Add color conditions
    for color in color_keywords:
        conditions.append(Product.colors.any(color))

    # If no specific keywords found, do a general text search
    if not conditions:
        query_words = query.split()
        for word in query_words:
            if len(word) > 2:
                conditions.append(Product.name.ilike(f"%{word}%"))
                conditions.append(Product.description.ilike(f"%{word}%"))

    # Execute query
    if conditions:
        stmt = (
            select(Product)
            .where(Product.is_active == True)
            .where(or_(*conditions))
            .order_by(Product.stock_count.desc())
            .limit(limit)
        )
    else:
        # Fallback: return top products by stock
        stmt = (
            select(Product)
            .where(Product.is_active == True)
            .order_by(Product.stock_count.desc())
            .limit(limit)
        )

    result = await db.execute(stmt)
    products = result.scalars().all()

    # Format products for response
    product_list = []
    for p in products:
        product_list.append(ProductInfo(
            id=str(p.id),
            name=p.name,
            price=float(p.price),
            sizes=p.sizes or [],
            colors=p.colors or [],
            stock_count=p.stock_count,
            description=p.description or ""
        ))

    return product_list, set(all_keywords)


def format_products_for_ai(products: List[ProductInfo]) -> str:
    """Format product list as text for AI prompt injection."""
    if not products:
        return "No products found matching the query."

    lines = ["RELEVANT PRODUCTS:"]

    for i, p in enumerate(products, 1):
        lines.append(f"\nProduct {i}: {p.name}")
        lines.append(f"  Price: {p.price:.2f} EGP")
        lines.append(f"  Available Sizes: {', '.join(p.sizes) if p.sizes else 'N/A'}")
        lines.append(f"  Available Colors: {', '.join(p.colors) if p.colors else 'N/A'}")
        lines.append(f"  In Stock: {p.stock_count} units")
        if p.description:
            lines.append(f"  Description: {p.description[:200]}")

    return "\n".join(lines)
