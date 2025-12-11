"""
Hybrid Search Engine combining Semantic (Qdrant) + Keyword (PostgreSQL FTS)
Provides best-of-both-worlds search with multilingual support.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.search.semantic import SemanticSearchEngine, SearchResult, get_semantic_search_engine
from app.search.multilingual import detect_language, enhance_query, extract_colors_multilingual, extract_product_types_multilingual

logger = logging.getLogger(__name__)


@dataclass
class HybridSearchResult:
    """
    Hybrid search result with combined scoring.
    """
    id: str
    semantic_score: float
    keyword_score: float
    combined_score: float
    payload: Dict[str, Any]
    source: str  # "semantic", "keyword", or "both"
    matched_fields: List[str]


class HybridSearchEngine:
    """
    Hybrid search engine combining semantic and keyword search.

    Strategy:
    1. Semantic-first: Always perform semantic search (multilingual)
    2. Keyword boost: Add FTS results for exact matches
    3. Intelligent fusion: Combine scores with configurable weights
    4. Result deduplication: Merge results by ID
    """

    def __init__(
        self,
        semantic_engine: Optional[SemanticSearchEngine] = None,
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4
    ):
        """
        Initialize hybrid search engine.

        Args:
            semantic_engine: Semantic search engine instance
            semantic_weight: Weight for semantic scores (0.0-1.0)
            keyword_weight: Weight for keyword scores (0.0-1.0)
        """
        self.semantic_engine = semantic_engine or get_semantic_search_engine()
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight

        logger.info(
            f"HybridSearchEngine initialized (semantic: {semantic_weight:.1f}, "
            f"keyword: {keyword_weight:.1f})"
        )

    async def search(
        self,
        query: str,
        db_session: AsyncSession,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        semantic_only: bool = False
    ) -> List[HybridSearchResult]:
        """
        Perform hybrid search combining semantic and keyword approaches.

        Args:
            query: Search query in any language
            db_session: Database session for FTS queries
            limit: Maximum number of results
            filters: Optional filters (category, price, stock)
            semantic_only: If True, skip keyword search (for very short queries)

        Returns:
            List of HybridSearchResult objects sorted by combined score
        """
        try:
            # Detect language for query enhancement
            language = detect_language(query)
            logger.info(f"Hybrid search query: '{query}' (language: {language})")

            # Execute semantic and keyword searches in parallel
            if semantic_only or len(query.split()) <= 2:
                # Very short queries: semantic only
                logger.info("Using semantic-only search (short query)")
                semantic_results = await self.semantic_engine.search(
                    query=query,
                    limit=limit,
                    filters=filters,
                    enhance_multilingual=True
                )
                keyword_results = []
            else:
                # Full hybrid search
                semantic_task = self.semantic_engine.search(
                    query=query,
                    limit=limit,
                    filters=filters,
                    enhance_multilingual=True
                )
                keyword_task = self._keyword_search(
                    query=query,
                    db_session=db_session,
                    limit=limit,
                    filters=filters
                )

                # Execute in parallel
                semantic_results, keyword_results = await asyncio.gather(
                    semantic_task,
                    keyword_task,
                    return_exceptions=True
                )

                # Handle exceptions
                if isinstance(semantic_results, Exception):
                    logger.error(f"Semantic search failed: {semantic_results}")
                    semantic_results = []
                if isinstance(keyword_results, Exception):
                    logger.error(f"Keyword search failed: {keyword_results}")
                    keyword_results = []

            # Combine and rank results
            combined_results = self._combine_results(
                semantic_results=semantic_results,
                keyword_results=keyword_results
            )

            logger.info(
                f"Hybrid search completed: {len(semantic_results)} semantic + "
                f"{len(keyword_results)} keyword = {len(combined_results)} combined"
            )

            return combined_results[:limit]

        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}", exc_info=True)
            return []

    async def _keyword_search(
        self,
        query: str,
        db_session: AsyncSession,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Perform PostgreSQL full-text search using GIN indexes.

        Args:
            query: Search query
            db_session: Database session
            limit: Maximum results
            filters: Optional filters

        Returns:
            List of (id, score, payload) tuples
        """
        try:
            # Enhance query for better FTS matching
            language = detect_language(query)
            enhanced_query = enhance_query(query, language)

            # Build FTS query (tsquery format)
            # Convert "blue hoodie" to "blue | hoodie" (OR) for better recall
            fts_terms = enhanced_query.split()
            tsquery = " | ".join(fts_terms)

            # Build SQL query with filters
            sql_parts = [
                "SELECT id, name, description, price, category, tags, in_stock,",
                "  ts_rank(search_vector, to_tsquery('english', :tsquery)) AS rank",
                "FROM products",
                "WHERE search_vector @@ to_tsquery('english', :tsquery)"
            ]

            # Add filters
            params = {"tsquery": tsquery, "limit": limit}

            if filters:
                if "category" in filters and filters["category"]:
                    sql_parts.append("  AND category = :category")
                    params["category"] = filters["category"]

                if "price_min" in filters:
                    sql_parts.append("  AND price >= :price_min")
                    params["price_min"] = filters["price_min"]

                if "price_max" in filters:
                    sql_parts.append("  AND price <= :price_max")
                    params["price_max"] = filters["price_max"]

                if "in_stock" in filters and filters["in_stock"] is not None:
                    sql_parts.append("  AND in_stock = :in_stock")
                    params["in_stock"] = filters["in_stock"]

            # Order by rank and limit
            sql_parts.append("ORDER BY rank DESC")
            sql_parts.append("LIMIT :limit")

            sql = "\n".join(sql_parts)

            # Execute query
            result = await db_session.execute(text(sql), params)
            rows = result.fetchall()

            # Convert to (id, score, payload) tuples
            keyword_results = []
            for row in rows:
                payload = {
                    "name": row.name,
                    "description": row.description,
                    "price": float(row.price) if row.price else None,
                    "category": row.category,
                    "tags": row.tags if row.tags else [],
                    "in_stock": row.in_stock
                }
                keyword_results.append((str(row.id), float(row.rank), payload))

            logger.info(f"FTS search returned {len(keyword_results)} results")
            return keyword_results

        except Exception as e:
            logger.error(f"Keyword search failed: {str(e)}", exc_info=True)
            return []

    def _combine_results(
        self,
        semantic_results: List[SearchResult],
        keyword_results: List[Tuple[str, float, Dict[str, Any]]]
    ) -> List[HybridSearchResult]:
        """
        Combine semantic and keyword results with score fusion.

        Uses Reciprocal Rank Fusion (RRF) for combining rankings:
        combined_score = semantic_weight * semantic_score + keyword_weight * keyword_score

        Args:
            semantic_results: Results from semantic search
            keyword_results: Results from keyword search

        Returns:
            List of HybridSearchResult sorted by combined score
        """
        # Build lookup maps
        semantic_map = {r.id: r for r in semantic_results}
        keyword_map = {id: (score, payload) for id, score, payload in keyword_results}

        # Collect all unique IDs
        all_ids = set(semantic_map.keys()) | set(keyword_map.keys())

        # Compute combined scores
        combined = []
        for id in all_ids:
            # Get semantic score (0.0 if not present)
            if id in semantic_map:
                semantic_result = semantic_map[id]
                semantic_score = semantic_result.score
                payload = semantic_result.payload
                matched_fields = semantic_result.matched_fields
                source = "semantic"
            else:
                semantic_score = 0.0
                payload = None
                matched_fields = []
                source = "keyword"

            # Get keyword score (0.0 if not present)
            if id in keyword_map:
                keyword_score, keyword_payload = keyword_map[id]
                if payload is None:
                    payload = keyword_payload
                if source == "semantic":
                    source = "both"
                    matched_fields.append("fts")
            else:
                keyword_score = 0.0

            # Compute combined score
            combined_score = (
                self.semantic_weight * semantic_score +
                self.keyword_weight * keyword_score
            )

            # Create hybrid result
            hybrid_result = HybridSearchResult(
                id=id,
                semantic_score=semantic_score,
                keyword_score=keyword_score,
                combined_score=combined_score,
                payload=payload or {},
                source=source,
                matched_fields=matched_fields
            )
            combined.append(hybrid_result)

        # Sort by combined score (descending)
        combined.sort(key=lambda x: x.combined_score, reverse=True)

        return combined

    async def search_with_filters_auto(
        self,
        query: str,
        db_session: AsyncSession,
        limit: int = 10
    ) -> List[HybridSearchResult]:
        """
        Smart search that automatically extracts filters from query.

        Examples:
        - "blue hoodie" → filters: {category: "hoodies", query: "blue"}
        - "cheap red shirt under $30" → filters: {price_max: 30, query: "red shirt"}

        Args:
            query: Natural language search query
            db_session: Database session
            limit: Maximum results

        Returns:
            List of search results with auto-extracted filters
        """
        # Extract product types
        product_types = extract_product_types_multilingual(query)

        # Extract colors
        colors = extract_colors_multilingual(query)

        # Build filters
        filters = {}

        # Add category filter if single product type detected
        if len(product_types) == 1:
            product_type, lang = product_types[0]
            filters["category"] = product_type
            logger.info(f"Auto-detected category: {product_type}")

        # Extract price from query (simple regex)
        import re
        price_pattern = r'\$(\d+)'
        price_matches = re.findall(price_pattern, query)
        if price_matches:
            max_price = int(price_matches[0])
            filters["price_max"] = max_price
            logger.info(f"Auto-detected price limit: ${max_price}")

        # Build cleaned query (remove filter terms)
        cleaned_query = query
        if product_types:
            for product_type, _ in product_types:
                cleaned_query = cleaned_query.replace(product_type, "")
        cleaned_query = re.sub(r'\$\d+', '', cleaned_query)
        cleaned_query = " ".join(cleaned_query.split())  # Clean whitespace

        logger.info(f"Smart search: '{query}' → cleaned: '{cleaned_query}' with filters: {filters}")

        # Perform search with extracted filters
        return await self.search(
            query=cleaned_query if cleaned_query else query,
            db_session=db_session,
            limit=limit,
            filters=filters if filters else None
        )


# Singleton instance
_hybrid_search_engine: Optional[HybridSearchEngine] = None


def get_hybrid_search_engine(
    semantic_weight: float = 0.6,
    keyword_weight: float = 0.4
) -> HybridSearchEngine:
    """Get or create the global hybrid search engine instance."""
    global _hybrid_search_engine
    if _hybrid_search_engine is None:
        _hybrid_search_engine = HybridSearchEngine(
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight
        )
    return _hybrid_search_engine
