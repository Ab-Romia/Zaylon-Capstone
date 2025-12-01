"""
Vector database service using Qdrant.
Manages collections, indexing, and similarity search.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
    ScoredPoint, PointIdsList
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VectorDatabase:
    """
    Qdrant vector database client for managing embeddings.
    Supports multiple collections for products and knowledge base.
    """

    def __init__(self):
        self.settings = settings
        self.client: Optional[QdrantClient] = None
        self._connect()

    def _connect(self):
        """Connect to Qdrant instance."""
        try:
            logger.info(f"Connecting to Qdrant at {self.settings.qdrant_url}")
            self.client = QdrantClient(
                url=self.settings.qdrant_url,
                api_key=self.settings.qdrant_api_key,
                timeout=10.0
            )
            logger.info("Successfully connected to Qdrant")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            # Don't raise - allow service to start, operations will fail gracefully
            self.client = None

    def is_connected(self) -> bool:
        """Check if connected to Qdrant."""
        if not self.client:
            return False
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    async def init_collections(self, embedding_dimension: int):
        """
        Initialize Qdrant collections for products and knowledge base.

        Args:
            embedding_dimension: Dimension of embedding vectors (1536 for OpenAI, 384 for local)
        """
        if not self.client:
            logger.error("Qdrant client not connected")
            return

        collections = [
            (self.settings.qdrant_collection_products, "Product embeddings"),
            (self.settings.qdrant_collection_knowledge, "Knowledge base embeddings")
        ]

        for collection_name, description in collections:
            try:
                # Check if collection exists
                collections_list = self.client.get_collections().collections
                exists = any(c.name == collection_name for c in collections_list)

                if not exists:
                    logger.info(f"Creating collection: {collection_name}")
                    self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=embedding_dimension,
                            distance=Distance.COSINE
                        )
                    )
                    logger.info(f"Created collection: {collection_name}")
                else:
                    # Validate existing collection has matching dimension
                    try:
                        collection_info = self.client.get_collection(collection_name)
                        existing_dim = collection_info.config.params.vectors.size
                        if existing_dim != embedding_dimension:
                            logger.warning(
                                f"Collection {collection_name} exists with dimension {existing_dim}, "
                                f"but expected {embedding_dimension}. Consider recreating the collection."
                            )
                        else:
                            logger.info(f"Collection already exists: {collection_name} (dimension: {existing_dim})")
                    except Exception as e:
                        logger.warning(f"Could not validate collection dimension: {e}")
            except Exception as e:
                logger.error(f"Failed to initialize collection {collection_name}: {e}")

    async def upsert_points(
        self,
        collection_name: str,
        points: List[Tuple[str, List[float], Dict[str, Any]]]
    ) -> bool:
        """
        Insert or update points in a collection.

        Args:
            collection_name: Name of the collection
            points: List of (id, vector, payload) tuples

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.error("Qdrant client not connected")
            return False

        if not points:
            logger.warning("No points to upsert")
            return True  # Not an error, just nothing to do

        try:
            point_structs = []
            for point_id, vector, payload in points:
                # Validate inputs
                if not vector:
                    logger.warning(f"Skipping point {point_id}: empty vector")
                    continue
                if payload is None:
                    payload = {}

                point_structs.append(
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                )

            if not point_structs:
                logger.warning("No valid points to upsert after validation")
                return False

            self.client.upsert(
                collection_name=collection_name,
                points=point_structs
            )
            logger.info(f"Upserted {len(point_structs)} points to {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert points: {e}")
            return False

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.

        Args:
            collection_name: Name of the collection
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
            filter_conditions: Optional filters on payload fields

        Returns:
            List of search results with id, score, and payload
        """
        if not self.client:
            logger.error("Qdrant client not connected")
            return []

        try:
            # Build filter if conditions provided
            query_filter = None
            if filter_conditions:
                conditions = []
                for field, value in filter_conditions.items():
                    conditions.append(
                        FieldCondition(
                            key=field,
                            match=MatchValue(value=value)
                        )
                    )
                if conditions:
                    query_filter = Filter(must=conditions)

            # Perform search using query_points (replaces deprecated search method)
            # Note: query_points returns a response object with .points attribute
            search_response = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter
            )

            # Format results with null checks
            # query_points returns a response object, access .points to get the list
            results = []
            for hit in search_response.points:
                results.append({
                    "id": str(hit.id),
                    "score": hit.score if hit.score is not None else 0.0,
                    "payload": hit.payload if hit.payload is not None else {}
                })

            logger.info(f"Found {len(results)} results in {collection_name}")
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def delete_points(
        self,
        collection_name: str,
        point_ids: List[str]
    ) -> bool:
        """
        Delete points from a collection.

        Args:
            collection_name: Name of the collection
            point_ids: List of point IDs to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.error("Qdrant client not connected")
            return False

        if not point_ids:
            logger.warning("No points to delete")
            return True

        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=PointIdsList(points=point_ids)
            )
            logger.info(f"Deleted {len(point_ids)} points from {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete points: {e}")
            return False

    async def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Collection info dict or None
        """
        if not self.client:
            return None

        try:
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return None

    async def count_points(self, collection_name: str) -> int:
        """
        Count points in a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Number of points
        """
        if not self.client:
            return 0

        try:
            info = self.client.get_collection(collection_name)
            return info.points_count or 0
        except Exception:
            return 0

    def close(self):
        """Close connection to Qdrant."""
        if self.client:
            self.client.close()
            logger.info("Qdrant connection closed")


# Global singleton instance
_vector_db: Optional[VectorDatabase] = None


def get_vector_db() -> VectorDatabase:
    """Get or create the global vector database instance."""
    global _vector_db
    if _vector_db is None:
        _vector_db = VectorDatabase()
    return _vector_db


async def init_vector_db(embedding_dimension: int):
    """Initialize vector database collections."""
    vector_db = get_vector_db()
    await vector_db.init_collections(embedding_dimension)


async def close_vector_db():
    """Close vector database connection."""
    global _vector_db
    if _vector_db:
        _vector_db.close()
        _vector_db = None
