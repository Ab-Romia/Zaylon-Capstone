"""
Semantic Search Engine using Qdrant Vector Database
Provides multilingual semantic similarity search for products and knowledge base.
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range
from app.core.config import get_settings
from app.services.embeddings import EmbeddingService
from app.search.multilingual import detect_language, enhance_query

settings = get_settings()

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Single search result with metadata."""
    id: str
    score: float
    payload: Dict[str, Any]
    matched_fields: List[str]


class SemanticSearchEngine:
    """
    Semantic search engine using Qdrant vector database.

    Features:
    - Multilingual query support (7 languages)
    - Query enhancement with synonyms
    - Filtered search (by category, price, availability)
    - Cross-lingual retrieval
    """

    def __init__(
        self,
        qdrant_client: Optional[QdrantClient] = None,
        embedding_service: Optional[EmbeddingService] = None,
        collection_name: str = settings.qdrant_collection_products
    ):
        """
        Initialize semantic search engine.

        Args:
            qdrant_client: Qdrant client instance (creates new if None)
            embedding_service: Embedding service instance (creates new if None)
            collection_name: Name of Qdrant collection to search
        """
        self.collection_name = collection_name

        # Initialize Qdrant client
        if qdrant_client is None:
            self.client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
                timeout=10.0
            )
        else:
            self.client = qdrant_client

        # Initialize embedding service
        if embedding_service is None:
            self.embedding_service = EmbeddingService()
        else:
            self.embedding_service = embedding_service

        logger.info(f"SemanticSearchEngine initialized for collection: {collection_name}")

    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        enhance_multilingual: bool = True,
        score_threshold: float = 0.5
    ) -> List[SearchResult]:
        """
        Perform semantic search on the collection.

        Args:
            query: Search query in any supported language
            limit: Maximum number of results to return
            filters: Optional filters (category, price_min, price_max, in_stock)
            enhance_multilingual: Whether to enhance query with synonyms
            score_threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List of SearchResult objects sorted by relevance
        """
        try:
            # Detect language
            language = detect_language(query)
            logger.info(f"Detected language: {language} for query: '{query}'")

            # Enhance query with multilingual synonyms
            if enhance_multilingual:
                enhanced_query = enhance_query(query, language)
                logger.info(f"Enhanced query: '{query}' → '{enhanced_query}'")
            else:
                enhanced_query = query

            # Generate embedding for search query
            query_vector = await self.embedding_service.get_embedding(enhanced_query)

            # Build Qdrant filters
            qdrant_filter = self._build_filter(filters) if filters else None

            # Perform vector search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=qdrant_filter
            )

            # Convert to SearchResult objects
            results = []
            for result in search_results:
                search_result = SearchResult(
                    id=str(result.id),
                    score=result.score,
                    payload=result.payload,
                    matched_fields=self._identify_matched_fields(result.payload, query)
                )
                results.append(search_result)

            logger.info(f"Semantic search returned {len(results)} results (threshold: {score_threshold})")
            return results

        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}", exc_info=True)
            return []

    async def search_knowledge_base(
        self,
        query: str,
        limit: int = 5,
        enhance_multilingual: bool = True,
        score_threshold: float = 0.6
    ) -> List[SearchResult]:
        """
        Search knowledge base (FAQs, policies) with higher threshold.

        Args:
            query: Question or query
            limit: Maximum number of results
            enhance_multilingual: Whether to enhance query
            score_threshold: Minimum similarity score (default higher for accuracy)

        Returns:
            List of relevant knowledge base documents
        """
        # Temporarily switch to knowledge base collection
        original_collection = self.collection_name
        self.collection_name = settings.qdrant_collection_knowledge

        try:
            results = await self.search(
                query=query,
                limit=limit,
                enhance_multilingual=enhance_multilingual,
                score_threshold=score_threshold
            )
            return results
        finally:
            # Restore original collection
            self.collection_name = original_collection

    def _build_filter(self, filters: Dict[str, Any]) -> Filter:
        """
        Build Qdrant filter from filter dictionary.

        Supported filters:
        - category: str (exact match)
        - price_min: float
        - price_max: float
        - in_stock: bool
        - tags: List[str] (any match)

        Args:
            filters: Dictionary of filter criteria

        Returns:
            Qdrant Filter object
        """
        conditions = []

        # Category filter (exact match)
        if "category" in filters and filters["category"]:
            conditions.append(
                FieldCondition(
                    key="category",
                    match=MatchValue(value=filters["category"])
                )
            )

        # Price range filter
        if "price_min" in filters or "price_max" in filters:
            price_range = {}
            if "price_min" in filters:
                price_range["gte"] = filters["price_min"]
            if "price_max" in filters:
                price_range["lte"] = filters["price_max"]

            conditions.append(
                FieldCondition(
                    key="price",
                    range=Range(**price_range)
                )
            )

        # Stock availability filter
        if "in_stock" in filters and filters["in_stock"] is not None:
            conditions.append(
                FieldCondition(
                    key="in_stock",
                    match=MatchValue(value=filters["in_stock"])
                )
            )

        # Tags filter (match any)
        if "tags" in filters and filters["tags"]:
            for tag in filters["tags"]:
                conditions.append(
                    FieldCondition(
                        key="tags",
                        match=MatchValue(value=tag)
                    )
                )

        # Combine all conditions with AND logic
        if conditions:
            return Filter(must=conditions)

        return None

    def _identify_matched_fields(self, payload: Dict[str, Any], query: str) -> List[str]:
        """
        Identify which fields in the payload likely matched the query.
        Used for debugging and explanation.

        Args:
            payload: Result payload
            query: Original search query

        Returns:
            List of field names that contain query terms
        """
        matched_fields = []
        query_terms = set(query.lower().split())

        # Check text fields
        text_fields = ["name", "description", "category"]
        for field in text_fields:
            if field in payload and payload[field]:
                field_value = str(payload[field]).lower()
                if any(term in field_value for term in query_terms):
                    matched_fields.append(field)

        # Check tags (list field)
        if "tags" in payload and payload["tags"]:
            tags_str = " ".join(str(tag).lower() for tag in payload["tags"])
            if any(term in tags_str for term in query_terms):
                matched_fields.append("tags")

        return matched_fields if matched_fields else ["semantic_similarity"]

    async def search_by_ids(self, ids: List[str]) -> List[SearchResult]:
        """
        Retrieve specific items by their IDs.

        Args:
            ids: List of item IDs to retrieve

        Returns:
            List of SearchResult objects
        """
        try:
            # Retrieve points by ID
            results = self.client.retrieve(
                collection_name=self.collection_name,
                ids=ids
            )

            # Convert to SearchResult objects
            search_results = []
            for result in results:
                search_results.append(
                    SearchResult(
                        id=str(result.id),
                        score=1.0,  # Perfect match (retrieved by ID)
                        payload=result.payload,
                        matched_fields=["id"]
                    )
                )

            return search_results

        except Exception as e:
            logger.error(f"Failed to retrieve by IDs: {str(e)}", exc_info=True)
            return []

    async def get_similar_products(
        self,
        product_id: str,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Find similar products to a given product (recommendation engine).

        Args:
            product_id: ID of the reference product
            limit: Maximum number of similar products
            filters: Optional filters to apply

        Returns:
            List of similar products
        """
        try:
            # Retrieve the reference product
            reference_products = await self.search_by_ids([product_id])

            if not reference_products:
                logger.warning(f"Product not found: {product_id}")
                return []

            reference_product = reference_products[0]

            # Use product name + description as search query
            search_query = f"{reference_product.payload.get('name', '')} {reference_product.payload.get('description', '')}"

            # Search for similar products
            similar_products = await self.search(
                query=search_query,
                limit=limit + 1,  # +1 because we'll filter out the original
                filters=filters,
                enhance_multilingual=False,  # Already in product language
                score_threshold=0.5
            )

            # Remove the original product from results
            similar_products = [p for p in similar_products if p.id != product_id]

            return similar_products[:limit]

        except Exception as e:
            logger.error(f"Failed to find similar products: {str(e)}", exc_info=True)
            return []

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.

        Returns:
            Dictionary with collection statistics
        """
        try:
            collection_info = self.client.get_collection(self.collection_name)

            return {
                "collection_name": self.collection_name,
                "points_count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "status": collection_info.status
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {"error": str(e)}


# Singleton instance for reuse
_semantic_search_engine: Optional[SemanticSearchEngine] = None


def get_semantic_search_engine() -> SemanticSearchEngine:
    """Get or create the global semantic search engine instance."""
    global _semantic_search_engine
    if _semantic_search_engine is None:
        _semantic_search_engine = SemanticSearchEngine()
    return _semantic_search_engine
