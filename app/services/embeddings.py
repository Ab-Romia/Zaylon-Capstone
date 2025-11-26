"""
Embedding service with OpenAI and local model support.
Supports multilingual embeddings (Arabic, English, Franco-Arabic).
"""
import logging
from typing import List, Optional
import numpy as np
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingService:
    """
    Unified embedding service supporting:
    - OpenAI embeddings (text-embedding-3-small)
    - Local Sentence Transformers (multilingual support)
    """

    def __init__(self):
        self.settings = settings
        self._openai_client = None
        self._local_model = None
        self._use_local = self.settings.use_local_embeddings  # Don't modify settings
        self._actual_dimension = None  # Detect actual dimension

        if not self._use_local:
            try:
                from openai import AsyncOpenAI
                if self.settings.openai_api_key:
                    self._openai_client = AsyncOpenAI(api_key=self.settings.openai_api_key)
                    logger.info("OpenAI embeddings initialized")
                else:
                    logger.warning("OpenAI API key not set, falling back to local embeddings")
                    self._use_local = True
            except ImportError:
                logger.warning("OpenAI package not available, falling back to local embeddings")
                self._use_local = True
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}, falling back to local embeddings")
                self._use_local = True

        if self._use_local or not self._openai_client:
            self._init_local_model()

    def _init_local_model(self):
        """Initialize local Sentence Transformer model."""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading local embedding model: {self.settings.local_embedding_model}")
            self._local_model = SentenceTransformer(self.settings.local_embedding_model)
            # Detect actual dimension from model
            test_embed = self._local_model.encode("test", convert_to_numpy=True)
            self._actual_dimension = len(test_embed)
            logger.info(f"Local embedding model loaded successfully (dimension: {self._actual_dimension})")
        except Exception as e:
            logger.error(f"Failed to load local embedding model: {e}")
            raise

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if self._use_local or not self._openai_client:
            return self._embed_local(text)
        else:
            return await self._embed_openai(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Filter empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            return []

        if self._use_local or not self._openai_client:
            return self._embed_local_batch(valid_texts)
        else:
            return await self._embed_openai_batch(valid_texts)

    async def _embed_openai(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        try:
            response = await self._openai_client.embeddings.create(
                model=self.settings.embedding_model,
                input=text
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated OpenAI embedding, dimension: {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}, falling back to local model")
            # Fallback to local model
            if not self._local_model:
                self._init_local_model()
            return self._embed_local(text)

    async def _embed_openai_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch using OpenAI API."""
        try:
            response = await self._openai_client.embeddings.create(
                model=self.settings.embedding_model,
                input=texts
            )
            embeddings = [item.embedding for item in response.data]
            logger.debug(f"Generated {len(embeddings)} OpenAI embeddings")
            return embeddings
        except Exception as e:
            logger.error(f"OpenAI batch embedding failed: {e}, falling back to local model")
            # Fallback to local model
            if not self._local_model:
                self._init_local_model()
            return self._embed_local_batch(texts)

    def _embed_local(self, text: str) -> List[float]:
        """Generate embedding using local Sentence Transformer."""
        try:
            embedding = self._local_model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Local embedding failed: {e}")
            raise

    def _embed_local_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch using local model."""
        try:
            embeddings = self._local_model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Local batch embedding failed: {e}")
            raise

    def get_dimension(self) -> int:
        """Get the dimension of embeddings produced by this service."""
        # Return detected dimension if available
        if self._actual_dimension is not None:
            return self._actual_dimension

        # Otherwise use defaults based on configuration
        if self._use_local or not self._openai_client:
            # Local model dimension (384 for MiniLM, but detect if possible)
            if self._local_model is not None:
                try:
                    test_embed = self._local_model.encode("test", convert_to_numpy=True)
                    self._actual_dimension = len(test_embed)
                    return self._actual_dimension
                except Exception:
                    pass
            return 384  # Fallback default
        else:
            # OpenAI text-embedding-3-small dimension
            return 1536

    async def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score between 0 and 1
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)


# Global singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
