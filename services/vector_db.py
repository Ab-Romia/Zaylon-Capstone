"""
Vector database service using Qdrant.
Manages collections, indexing, and similarity search.
"""
import logging
import warnings
import uuid
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
    ScoredPoint, PointIdsList
)
from config import get_settings

# Suppress Pydantic validation warnings from Qdrant client globally
# Qdrant server returns config fields that the Python client's Pydantic models don't expect
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

# Suppress Qdrant "unsecure connection" warning for local development
# This is safe for local Qdrant instances (http://localhost:6333)
warnings.filterwarnings("ignore", message=".*Api key is used with unsecure connection.*")


@contextmanager
def suppress_pydantic_warnings():
    """Context manager to suppress Pydantic validation warnings from Qdrant responses."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*validation error.*")
        warnings.filterwarnings("ignore", message=".*Extra inputs are not permitted.*")
        warnings.filterwarnings("ignore", message=".*Input should be a valid.*")
        yield

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

            # Suppress warnings during connection
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                self.client = QdrantClient(
                    url=self.settings.qdrant_url,
                    api_key=self.settings.qdrant_api_key,
                    timeout=10.0
                )

            # Test the connection
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                self.client.get_collections()

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
            # Suppress warnings during connection check
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                # Quick connection test
                self.client.get_collections()
            return True
        except Exception as e:
            logger.debug(f"Qdrant connection check failed: {e}")
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
                        with suppress_pydantic_warnings():
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
            import json

            point_structs = []
            for point_id, vector, payload in points:
                # Validate inputs
                if not vector:
                    logger.warning(f"Skipping point {point_id}: empty vector")
                    continue
                if payload is None:
                    payload = {}

                # Qdrant requires point IDs to be either UUID strings or integers
                # Preserve the type - don't convert integers to strings
                if isinstance(point_id, int):
                    final_id = point_id
                else:
                    # Ensure string IDs are valid UUIDs or keep as string
                    final_id = str(point_id) if point_id else str(uuid.uuid4())

                # Convert vector to list if it's numpy array
                if hasattr(vector, 'tolist'):
                    vector = vector.tolist()

                # Ensure vector is a flat list of floats
                if not isinstance(vector, list):
                    vector = list(vector)

                # Clean payload to ensure it's JSON-serializable
                # Remove any non-serializable types
                clean_payload = {}
                for key, value in payload.items():
                    try:
                        # Test if value is JSON-serializable
                        json.dumps(value)
                        clean_payload[key] = value
                    except (TypeError, ValueError):
                        # Convert non-serializable types to string
                        clean_payload[key] = str(value)

                point_structs.append(
                    PointStruct(
                        id=final_id,  # Use properly typed ID
                        vector=vector,
                        payload=clean_payload
                    )
                )

            if not point_structs:
                logger.warning("No valid points to upsert after validation")
                return False

            # Upsert points with proper error handling
            with suppress_pydantic_warnings():
                self.client.upsert(
                    collection_name=collection_name,
                    points=point_structs
                )
            logger.info(f"Upserted {len(point_structs)} points to {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert points: {e}")
            # Log the first point for debugging
            if points:
                logger.debug(f"Sample point structure: {points[0]}")
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

            # Perform search
            search_results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter
            )

            # Format results with null checks
            results = []
            for hit in search_results:
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
            with suppress_pydantic_warnings():
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
            with suppress_pydantic_warnings():
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
