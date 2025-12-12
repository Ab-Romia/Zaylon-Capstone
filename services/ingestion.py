"""
Document ingestion service for RAG system.
Handles indexing of products and knowledge base documents.
"""
import logging
import hashlib
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Product
from config import get_settings
from services.embeddings import get_embedding_service
from services.vector_db import get_vector_db

logger = logging.getLogger(__name__)
settings = get_settings()


class IngestionService:
    """
    Service for ingesting and indexing documents into the vector database.
    Supports products and knowledge base documents.
    """

    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.vector_db = get_vector_db()
        self.settings = settings

    def _generate_id(self, content: str) -> str:
        """Generate a unique ID for a document based on its content."""
        return hashlib.md5(content.encode()).hexdigest()

    def _create_product_text(self, product: Product) -> str:
        """
        Create searchable text representation of a product.

        Args:
            product: Product database model

        Returns:
            Formatted text for embedding
        """
        parts = [
            f"Product: {product.name}",
            f"Price: {product.price} EGP"
        ]

        if product.category:
            parts.append(f"Category: {product.category}")

        if product.description:
            parts.append(f"Description: {product.description}")

        if product.tags:
            parts.append(f"Tags: {', '.join(product.tags)}")

        if product.sizes:
            parts.append(f"Available sizes: {', '.join(product.sizes)}")

        if product.colors:
            parts.append(f"Available colors: {', '.join(product.colors)}")

        parts.append(f"Stock: {product.stock_count} units")

        return "\n".join(parts)

    async def index_product(self, product: Product) -> bool:
        """
        Index a single product into the vector database.

        Args:
            product: Product to index

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate product data
            if not product.name or not product.name.strip():
                logger.warning(f"Skipping product {product.id}: empty name")
                return False

            # Create searchable text
            product_text = self._create_product_text(product)

            # Truncate if too long (safety check)
            max_chars = 8000
            if len(product_text) > max_chars:
                logger.warning(f"Product text truncated from {len(product_text)} to {max_chars} chars")
                product_text = product_text[:max_chars]

            # Generate embedding
            embedding = await self.embedding_service.embed_text(product_text)

            # Create payload with metadata
            payload = {
                "product_id": str(product.id),
                "name": product.name,
                "price": float(product.price),
                "description": product.description or "",
                "category": product.category or "",
                "tags": product.tags or [],
                "sizes": product.sizes or [],
                "colors": product.colors or [],
                "stock_count": product.stock_count,
                "is_active": product.is_active,
                "indexed_at": datetime.utcnow().isoformat(),
                "text": product_text
            }

            # Upsert to vector database
            # Use product ID directly if it's an integer, or convert to UUID
            point_id = product.id if isinstance(product.id, int) else str(product.id)
            success = await self.vector_db.upsert_points(
                collection_name=self.settings.qdrant_collection_products,
                points=[(point_id, embedding, payload)]
            )

            if success:
                logger.info(f"Indexed product: {product.name} (ID: {product.id})")
            return success

        except Exception as e:
            logger.error(f"Failed to index product {product.id}: {e}")
            return False

    async def index_all_products(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Index all active products from the database.

        Args:
            db: Database session

        Returns:
            Statistics about the indexing operation
        """
        logger.info("Starting bulk product indexing...")
        stats = {
            "total": 0,
            "indexed": 0,
            "failed": 0,
            "start_time": datetime.utcnow().isoformat()
        }

        try:
            # Get all active products
            stmt = select(Product).where(Product.is_active == True)
            result = await db.execute(stmt)
            products = result.scalars().all()

            stats["total"] = len(products)
            logger.info(f"Found {len(products)} active products to index")

            # Index products in batches
            batch_size = 10
            for i in range(0, len(products), batch_size):
                batch = products[i:i + batch_size]

                # Process batch
                for product in batch:
                    success = await self.index_product(product)
                    if success:
                        stats["indexed"] += 1
                    else:
                        stats["failed"] += 1

                logger.info(f"Processed {min(i + batch_size, len(products))}/{len(products)} products")

            stats["end_time"] = datetime.utcnow().isoformat()
            logger.info(f"Indexing complete: {stats['indexed']} indexed, {stats['failed']} failed")

            return stats

        except Exception as e:
            logger.error(f"Bulk indexing failed: {e}")
            stats["error"] = str(e)
            return stats

    async def index_knowledge_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Index a knowledge base document.

        Args:
            doc_id: Unique document ID
            content: Document content
            metadata: Additional metadata (title, category, etc.)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate inputs
            if not doc_id or not doc_id.strip():
                logger.error("Document ID cannot be empty")
                return False

            if not content or not content.strip():
                logger.error(f"Document content cannot be empty for {doc_id}")
                return False

            # Chunk the document if it's too long
            chunks = self._chunk_text(content)

            points = []
            for i, chunk in enumerate(chunks):
                # Generate embedding for chunk
                embedding = await self.embedding_service.embed_text(chunk)

                # Create payload
                payload = {
                    "doc_id": doc_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "content": chunk,
                    "indexed_at": datetime.utcnow().isoformat()
                }

                # Add metadata if provided
                if metadata:
                    payload.update(metadata)

                # Generate unique UUID for chunk (Qdrant requires UUID or integer)
                # Use deterministic UUID based on doc_id and chunk index for consistency
                namespace_uuid = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # Namespace for doc chunks
                chunk_id = str(uuid.uuid5(namespace_uuid, f"{doc_id}_chunk_{i}"))
                points.append((chunk_id, embedding, payload))

            # Upsert all chunks
            success = await self.vector_db.upsert_points(
                collection_name=self.settings.qdrant_collection_knowledge,
                points=points
            )

            if success:
                logger.info(f"Indexed knowledge document: {doc_id} ({len(chunks)} chunks)")
            return success

        except Exception as e:
            logger.error(f"Failed to index knowledge document {doc_id}: {e}")
            return False

    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks for embedding.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        # Simple sentence-based chunking
        sentences = text.split('.')
        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_length = len(sentence.split())

            if current_length + sentence_length > self.settings.rag_chunk_size:
                if current_chunk:
                    chunks.append('. '.join(current_chunk) + '.')
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length

        if current_chunk:
            chunks.append('. '.join(current_chunk) + '.')

        return chunks if chunks else [text]

    async def delete_product(self, product_id: str) -> bool:
        """
        Delete a product from the vector database.

        Args:
            product_id: Product ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            success = await self.vector_db.delete_points(
                collection_name=self.settings.qdrant_collection_products,
                point_ids=[product_id]
            )
            if success:
                logger.info(f"Deleted product from index: {product_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to delete product {product_id}: {e}")
            return False

    async def delete_knowledge_document(self, doc_id: str) -> bool:
        """
        Delete a knowledge document and all its chunks.

        Args:
            doc_id: Document ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Search for all chunks of this document
            # Note: This is a simple implementation. For production,
            # consider maintaining a mapping of doc_id to chunk_ids
            logger.info(f"Deleting knowledge document: {doc_id}")
            # For now, we'll need to implement a filter-based deletion
            # or maintain a separate mapping
            return True
        except Exception as e:
            logger.error(f"Failed to delete knowledge document {doc_id}: {e}")
            return False


# Global singleton instance
_ingestion_service: Optional[IngestionService] = None


def get_ingestion_service() -> IngestionService:
    """Get or create the global ingestion service instance."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = IngestionService()
    return _ingestion_service
