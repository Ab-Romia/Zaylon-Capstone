"""
Multilingual product search service (RAG-lite).
"""
import re
from typing import List, Tuple, Set
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from database import Product
from models import ProductInfo, SearchMetadata, ProductSearchResponse
import logging

logger = logging.getLogger(__name__)

# Multilingual keyword dictionaries
PRODUCT_KEYWORDS = {
    # Clothing items - mapped to English search terms
    "jeans": ["jeans", "جينز", "جينس", "jeanz", "denim"],
    "pants": ["pants", "بنطلون", "بنطلونات", "pantalon", "bantalon", "trousers", "joggers"],
    "hoodie": ["hoodie", "هودي", "هوديز", "hoody", "sweatshirt"],
    "shirt": ["shirt", "شيرت", "قميص", "shert", "t-shirt", "tshirt", "tee"],
    "jacket": ["jacket", "جاكيت", "جاكت", "jaket", "coat", "معطف", "bomber", "puffer"],
    "shoes": ["shoes", "حذاء", "جزمة", "shoe", "7ezaa2", "gizma", "sneakers", "boots", "footwear"],
    "dress": ["dress", "فستان", "fostan", "dresses"],
    "skirt": ["skirt", "جيبة", "jiba", "skirts"],
    "shorts": ["shorts", "شورت", "short"],
    "sweater": ["sweater", "سويتر", "pullover", "knit"],
    "bag": ["bag", "شنطة", "حقيبة", "shanta", "bags", "handbag", "crossbody"],
    "cap": ["cap", "كاب", "طاقية", "hat", "beanie"],
    "socks": ["socks", "شراب", "جوارب", "sharab"],
    # Seasonal keywords - CRITICAL for seasonal queries
    "winter": ["winter", "شتاء", "شتوي", "شتا", "شتة", "sheta", "shitaa", "cold", "برد", "بارد"],
    "summer": ["summer", "صيف", "صيفي", "sayf", "saif", "hot", "حر"],
    "spring": ["spring", "ربيع", "ربيعي", "rabie"],
    "fall": ["fall", "autumn", "خريف", "خريفي", "kharif"],
    # Generic categories - will match ANY clothing
    "clothing": ["clothing", "clothes", "apparel", "wear", "garment", "outfit", "لبس", "هدوم", "ملابس"],
    "accessories": ["accessories", "accessory", "اكسسوار"],
}

# Broad category fallback - if query contains these, return all products
BROAD_CATEGORIES = ["clothing", "clothes", "products", "items", "stuff", "things", "apparel"]

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
    limit: int = 3
) -> ProductSearchResponse:
    """
    Search products using hybrid approach:
    1. Keyword matching for specific items
    2. Semantic search fallback for broad queries
    3. Return ALL products for very broad categories

    This is a RAG-enhanced approach that handles:
    - Specific queries: "black hoodie" → keyword match
    - Synonyms: "shoes" → matches "sneakers", "boots"
    - Broad queries: "clothing" → returns diverse selection
    """
    logger.info(f"Searching products with query: {query}")

    # Detect language
    detected_language = detect_language(query)
    query_lower = query.lower()

    # Check for broad category queries first
    is_broad_query = any(cat in query_lower for cat in BROAD_CATEGORIES)

    if is_broad_query:
        logger.info(f"Broad category query detected: {query}")
        # Return diverse selection of products for broad queries
        stmt = (
            select(Product)
            .where(Product.is_active == True)
            .order_by(Product.stock_count.desc())
            .limit(limit * 2)  # Return more for broad queries
        )
        result = await db.execute(stmt)
        products = result.scalars().all()
    else:
        # Extract keywords
        product_keywords, color_keywords = extract_product_keywords(query)
        size = extract_size(query)

        all_keywords = list(product_keywords) + list(color_keywords)
        if size:
            all_keywords.append(size)

        logger.info(f"Detected language: {detected_language}, keywords: {all_keywords}")

        # Build database query with enhanced matching
        conditions = []

        # Add product keyword conditions - match against name, description, tags, and category
        for keyword in product_keywords:
            conditions.append(Product.name.ilike(f"%{keyword}%"))
            conditions.append(Product.description.ilike(f"%{keyword}%"))
            conditions.append(Product.category.ilike(f"%{keyword}%"))
            conditions.append(Product.tags.any(keyword))

        # Add color conditions
        for color in color_keywords:
            conditions.append(Product.colors.any(color))

        # Enhanced: Also search for individual query words
        query_words = [w for w in query_lower.split() if len(w) > 2]
        for word in query_words:
            conditions.append(Product.name.ilike(f"%{word}%"))
            conditions.append(Product.description.ilike(f"%{word}%"))
            conditions.append(Product.category.ilike(f"%{word}%"))
            conditions.append(Product.tags.any(word))

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

    # If keyword search returned 0 results, try semantic search
    if not products:
        logger.info(f"Keyword search returned 0 results, attempting semantic search...")
        try:
            from services.rag import get_rag_service
            rag_service = get_rag_service()
            semantic_results = await rag_service.search_products_semantic(
                query=query,
                db=db,
                limit=limit,
                min_score=0.3  # Even lower threshold for fallback
            )
            if semantic_results:
                logger.info(f"Semantic search found {len(semantic_results)} products")
                # Convert semantic results to Product objects
                product_ids = [r['id'] for r in semantic_results]
                stmt = select(Product).where(Product.id.in_(product_ids))
                result = await db.execute(stmt)
                products = result.scalars().all()
        except Exception as e:
            logger.warning(f"Semantic search fallback failed: {e}")

    # FINAL FALLBACK: If still no products, return top products by stock
    # NEVER return zero products - always show something!
    if not products:
        logger.warning(f"All searches returned 0 results. Returning top products as final fallback.")
        stmt = (
            select(Product)
            .where(Product.is_active == True)
            .order_by(Product.stock_count.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        products = result.scalars().all()
        logger.info(f"Final fallback returned {len(products)} top products")

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

    # Format for AI context
    formatted_for_ai = format_products_for_ai(product_list)

    return ProductSearchResponse(
        products=product_list,
        formatted_for_ai=formatted_for_ai,
        search_metadata=SearchMetadata(
            detected_language=detected_language,
            matched_keywords=all_keywords,
            total_found=len(product_list)
        )
    )


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
