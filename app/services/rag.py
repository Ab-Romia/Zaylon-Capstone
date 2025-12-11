"""
RAG (Retrieval-Augmented Generation) orchestration service.
Combines semantic search with keyword matching for optimal DM assistant responses.
PHASE 2: Enhanced with multilingual semantic search and query enhancement.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product
from app.core.config import get_settings
from app.services.embeddings import get_embedding_service
from app.services.vector_db import get_vector_db
from app.services.products import extract_product_keywords, extract_size, detect_language
from app.search.semantic import get_semantic_search_engine
from app.search.multilingual import enhance_query, detect_language as detect_lang_v2

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGService:
    """
    RAG orchestration service for the DM assistant.
    Provides hybrid search (semantic + keyword) and context preparation.
    """

    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.vector_db = get_vector_db()
        self.settings = settings

    async def search_products_semantic(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 5,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Semantic product search using vector similarity.

        Args:
            query: User query
            db: Database session
            limit: Maximum number of results
            min_score: Minimum similarity score

        Returns:
            List of products with relevance scores
        """
        try:
            # Check if vector DB is available
            if not self.vector_db.is_connected():
                logger.warning("Vector DB not connected, falling back to keyword search")
                return []

            # Generate query embedding
            query_embedding = await self.embedding_service.embed_text(query)

            # Search vector database
            results = await self.vector_db.search(
                collection_name=self.settings.qdrant_collection_products,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=min_score
            )

            # Format results
            products = []
            for result in results:
                payload = result["payload"]
                products.append({
                    "id": payload.get("product_id"),
                    "name": payload.get("name"),
                    "price": payload.get("price"),
                    "description": payload.get("description"),
                    "sizes": payload.get("sizes", []),
                    "colors": payload.get("colors", []),
                    "stock_count": payload.get("stock_count"),
                    "similarity_score": result["score"],
                    "search_method": "semantic"
                })

            logger.info(f"Semantic search found {len(products)} products")
            return products

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    async def search_products_keyword(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Keyword-based product search (fallback/complement to semantic search).

        Args:
            query: User query
            db: Database session
            limit: Maximum number of results

        Returns:
            List of products
        """
        try:
            # Extract keywords
            product_keywords, color_keywords = extract_product_keywords(query)
            all_keywords = list(product_keywords) + list(color_keywords)

            if not all_keywords:
                # Fallback: use query words
                all_keywords = [w for w in query.split() if len(w) > 2]

            # Build database query
            conditions = []
            for keyword in product_keywords:
                conditions.append(Product.name.ilike(f"%{keyword}%"))
                conditions.append(Product.description.ilike(f"%{keyword}%"))

            for color in color_keywords:
                conditions.append(Product.colors.any(color))

            if not conditions:
                for word in all_keywords:
                    conditions.append(Product.name.ilike(f"%{word}%"))
                    conditions.append(Product.description.ilike(f"%{word}%"))

            if conditions:
                stmt = (
                    select(Product)
                    .where(Product.is_active == True)
                    .where(or_(*conditions))
                    .order_by(Product.stock_count.desc())
                    .limit(limit)
                )
            else:
                stmt = (
                    select(Product)
                    .where(Product.is_active == True)
                    .order_by(Product.stock_count.desc())
                    .limit(limit)
                )

            result = await db.execute(stmt)
            products_db = result.scalars().all()

            products = []
            for p in products_db:
                products.append({
                    "id": str(p.id),
                    "name": p.name,
                    "price": float(p.price),
                    "description": p.description or "",
                    "sizes": p.sizes or [],
                    "colors": p.colors or [],
                    "stock_count": p.stock_count,
                    "similarity_score": 0.5,  # Default score for keyword matches
                    "search_method": "keyword"
                })

            logger.info(f"Keyword search found {len(products)} products")
            return products

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    async def search_products_hybrid(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 5
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Hybrid search combining semantic and keyword approaches.
        OPTIMIZED: Runs semantic and keyword search in parallel.
        """
        import asyncio
        detected_language = detect_language(query)

        # PARALLEL EXECUTION: Run both searches concurrently
        async def empty_search():
            return []

        semantic_task = (
            self.search_products_semantic(query, db, limit=limit, min_score=self.settings.rag_similarity_threshold)
            if self.settings.enable_semantic_search
            else empty_search()
        )
        keyword_task = self.search_products_keyword(query, db, limit=limit)

        results = await asyncio.gather(semantic_task, keyword_task, return_exceptions=True)

        semantic_results = results[0] if not isinstance(results[0], Exception) else []
        keyword_results = results[1] if not isinstance(results[1], Exception) else []

        # Merge and deduplicate results
        seen_ids = set()
        merged_results = []

        # Prioritize semantic results (higher quality)
        for product in semantic_results:
            product_id = product["id"]
            if product_id not in seen_ids:
                seen_ids.add(product_id)
                merged_results.append(product)

        # Add keyword results that weren't found semantically
        for product in keyword_results:
            product_id = product["id"]
            if product_id not in seen_ids:
                seen_ids.add(product_id)
                merged_results.append(product)

        # Sort by similarity score
        merged_results.sort(key=lambda x: x["similarity_score"], reverse=True)

        # Limit results
        final_results = merged_results[:limit]

        # Build metadata
        metadata = {
            "detected_language": detected_language,
            "total_found": len(final_results),
            "semantic_count": len(semantic_results),
            "keyword_count": len(keyword_results),
            "hybrid_enabled": self.settings.enable_hybrid_search
        }

        logger.info(
            f"Hybrid search: {len(semantic_results)} semantic + "
            f"{len(keyword_results)} keyword = {len(final_results)} final"
        )

        return final_results, metadata

    async def search_knowledge_base(
        self,
        query: str,
        limit: int = 3,
        category: Optional[str] = None,
        use_enhanced_search: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search knowledge base for relevant information.
        PHASE 2: Enhanced with multilingual support and query enhancement.

        Args:
            query: User query in any language
            limit: Maximum number of results
            category: Optional category filter
            use_enhanced_search: If True, use new semantic search engine with multilingual support

        Returns:
            List of relevant knowledge base entries
        """
        try:
            if use_enhanced_search:
                # PHASE 2: Use new semantic search engine with multilingual support
                semantic_engine = get_semantic_search_engine()

                # Detect language and enhance query
                language = detect_lang_v2(query)
                logger.info(f"Knowledge base search - language: {language}, query: '{query}'")

                # Build filters
                filters = {}
                if category:
                    filters["category"] = category

                # Perform semantic search on knowledge base
                results = await semantic_engine.search_knowledge_base(
                    query=query,
                    limit=limit,
                    enhance_multilingual=True,
                    score_threshold=self.settings.rag_similarity_threshold
                )

                # Convert SearchResult to knowledge item format
                knowledge_items = []
                for result in results:
                    payload = result.payload
                    knowledge_items.append({
                        "doc_id": payload.get("doc_id"),
                        "content": payload.get("content"),
                        "category": payload.get("category"),
                        "title": payload.get("title"),
                        "similarity_score": result.score,
                        "language": language,
                        "matched_fields": result.matched_fields
                    })

                logger.info(
                    f"Enhanced knowledge base search found {len(knowledge_items)} items "
                    f"(language: {language}, threshold: {self.settings.rag_similarity_threshold})"
                )
                return knowledge_items

            else:
                # Fallback to old implementation
                if not self.vector_db.is_connected():
                    logger.warning("Vector DB not connected")
                    return []

                # Generate query embedding
                query_embedding = await self.embedding_service.embed_text(query)

                # Build filter if category provided
                filter_conditions = {}
                if category:
                    filter_conditions["category"] = category

                # Search vector database
                results = await self.vector_db.search(
                    collection_name=self.settings.qdrant_collection_knowledge,
                    query_vector=query_embedding,
                    limit=limit,
                    score_threshold=self.settings.rag_similarity_threshold,
                    filter_conditions=filter_conditions
                )

                # Format results
                knowledge_items = []
                for result in results:
                    payload = result["payload"]
                    knowledge_items.append({
                        "doc_id": payload.get("doc_id"),
                        "content": payload.get("content"),
                        "category": payload.get("category"),
                        "title": payload.get("title"),
                        "similarity_score": result["score"]
                    })

                logger.info(f"Knowledge base search found {len(knowledge_items)} items")
                return knowledge_items

        except Exception as e:
            logger.error(f"Knowledge base search failed: {e}", exc_info=True)
            return []

    def format_products_for_ai(self, products: List[Dict[str, Any]]) -> str:
        """
        Format products for AI context injection.

        Args:
            products: List of product dicts

        Returns:
            Formatted string for AI prompt
        """
        if not products:
            return "No relevant products found."

        lines = ["RELEVANT PRODUCTS (Retrieved using AI-powered semantic search):"]

        for i, p in enumerate(products, 1):
            lines.append(f"\nProduct {i}: {p['name']}")
            lines.append(f"  Price: {p['price']:.2f} EGP")
            lines.append(f"  Available Sizes: {', '.join(p['sizes']) if p['sizes'] else 'N/A'}")
            lines.append(f"  Available Colors: {', '.join(p['colors']) if p['colors'] else 'N/A'}")
            lines.append(f"  In Stock: {p['stock_count']} units")
            if p.get('description'):
                lines.append(f"  Description: {p['description'][:200]}")
            lines.append(f"  Relevance: {p['similarity_score']:.2f} ({p['search_method']})")

        return "\n".join(lines)

    def format_knowledge_for_ai(self, knowledge_items: List[Dict[str, Any]]) -> str:
        """
        Format knowledge base items for AI context injection.

        Args:
            knowledge_items: List of knowledge items

        Returns:
            Formatted string for AI prompt
        """
        if not knowledge_items:
            return ""

        lines = ["RELEVANT INFORMATION FROM KNOWLEDGE BASE:"]

        for i, item in enumerate(knowledge_items, 1):
            title = item.get("title", "Information")
            content = item.get("content", "")
            lines.append(f"\n{i}. {title}")
            lines.append(f"   {content}")
            lines.append(f"   (Relevance: {item['similarity_score']:.2f})")

        return "\n".join(lines)

    async def prepare_rag_context(
        self,
        query: str,
        db: AsyncSession,
        include_knowledge: bool = True
    ) -> Dict[str, Any]:
        """
        Prepare complete RAG context for DM assistant.

        Args:
            query: User query
            db: Database session
            include_knowledge: Whether to include knowledge base results

        Returns:
            Complete context dict with products and knowledge
        """
        # Search products using hybrid approach
        products, product_metadata = await self.search_products_hybrid(
            query, db, limit=self.settings.rag_top_k
        )

        # Search knowledge base
        knowledge_items = []
        if include_knowledge and self.settings.enable_knowledge_base:
            knowledge_items = await self.search_knowledge_base(query, limit=3)

        # Format for AI
        products_formatted = self.format_products_for_ai(products)
        knowledge_formatted = self.format_knowledge_for_ai(knowledge_items)

        return {
            "products": products,
            "products_formatted": products_formatted,
            "product_metadata": product_metadata,
            "knowledge_items": knowledge_items,
            "knowledge_formatted": knowledge_formatted,
            "rag_enabled": True
        }


# Global singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get or create the global RAG service instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
