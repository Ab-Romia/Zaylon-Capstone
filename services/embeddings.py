"""
Embedding service with OpenAI and local model support.
Supports multilingual embeddings (Arabic, English, Franco-Arabic).
"""
import logging
from typing import List, Optional
import numpy as np
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingService:
    """
    Unified embedding service supporting:
    - OpenAI embeddings (text-embedding-3-small, dimension: 1536)
    - Google Gemini embeddings (text-embedding-004, dimension: 768)
    - Local Sentence Transformers (multilingual support, dimension: 384)
    """

    def __init__(self):
        self.settings = settings
        self._openai_client = None
        self._gemini_client = None
        self._local_model = None
        self._use_local = self.settings.use_local_embeddings
        self._provider = None  # Will be "openai", "gemini", or "local"
        self._actual_dimension = None

        # Determine which provider to use
        if self._use_local:
            self._provider = "local"
            self._init_local_model()
        else:
            # Try to initialize based on LLM provider preference
            llm_provider = self.settings.llm_provider.lower()

            if llm_provider == "gemini":
                # Try Gemini first
                if self._init_gemini():
                    self._provider = "gemini"
                elif self._init_openai():
                    self._provider = "openai"
                    logger.warning("Gemini embeddings unavailable, using OpenAI")
                else:
                    self._provider = "local"
                    self._init_local_model()
                    logger.warning("Cloud embeddings unavailable, using local model")
            else:
                # Try OpenAI first (default)
                if self._init_openai():
                    self._provider = "openai"
                elif self._init_gemini():
                    self._provider = "gemini"
                    logger.warning("OpenAI embeddings unavailable, using Gemini")
                else:
                    self._provider = "local"
                    self._init_local_model()
                    logger.warning("Cloud embeddings unavailable, using local model")

        logger.info(f"Embedding service initialized with provider: {self._provider}")

    def _init_openai(self) -> bool:
        """Initialize OpenAI client with proper timeout configuration. Returns True if successful."""
        try:
            from openai import AsyncOpenAI
            import httpx
            if self.settings.openai_api_key:
                # Configure timeout to 60 seconds to prevent aggressive retries
                # This reduces latency issues caused by premature timeouts
                self._openai_client = AsyncOpenAI(
                    api_key=self.settings.openai_api_key,
                    timeout=httpx.Timeout(60.0, connect=10.0),  # 60s total, 10s connect
                    max_retries=2  # Limit retries to prevent compounding latency
                )
                logger.info("OpenAI embeddings initialized with 60s timeout")
                return True
        except Exception as e:
            logger.error(f"OpenAI initialization failed: {e}")
        return False

    def _init_gemini(self) -> bool:
        """Initialize Gemini client. Returns True if successful."""
        try:
            import google.generativeai as genai
            if self.settings.gemini_api_key:
                genai.configure(api_key=self.settings.gemini_api_key)
                self._gemini_client = genai
                logger.info("Gemini embeddings initialized")
                return True
        except Exception as e:
            logger.debug(f"Gemini initialization failed: {e}")
        return False

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

        if self._provider == "openai":
            return await self._embed_openai(text)
        elif self._provider == "gemini":
            return await self._embed_gemini(text)
        else:  # local
            return self._embed_local(text)

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

        if self._provider == "openai":
            return await self._embed_openai_batch(valid_texts)
        elif self._provider == "gemini":
            return await self._embed_gemini_batch(valid_texts)
        else:  # local
            return self._embed_local_batch(valid_texts)

    async def _embed_openai(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API. NO FALLBACK - fails if OpenAI unavailable."""
        try:
            response = await self._openai_client.embeddings.create(
                model=self.settings.embedding_model,
                input=text
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated OpenAI embedding, dimension: {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise  # No fallback - fail explicitly

    async def _embed_openai_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch using OpenAI API. NO FALLBACK - fails if OpenAI unavailable."""
        try:
            response = await self._openai_client.embeddings.create(
                model=self.settings.embedding_model,
                input=texts
            )
            embeddings = [item.embedding for item in response.data]
            logger.debug(f"Generated {len(embeddings)} OpenAI embeddings")
            return embeddings
        except Exception as e:
            logger.error(f"OpenAI batch embedding failed: {e}")
            raise  # No fallback - fail explicitly

    async def _embed_gemini(self, text: str) -> List[float]:
        """Generate embedding using Gemini API. NO FALLBACK - fails if Gemini unavailable."""
        try:
            result = self._gemini_client.embed_content(
                model=self.settings.gemini_embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            embedding = result['embedding']
            logger.debug(f"Generated Gemini embedding, dimension: {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"Gemini embedding failed: {e}")
            raise  # No fallback - fail explicitly

    async def _embed_gemini_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch using Gemini API. NO FALLBACK - fails if Gemini unavailable."""
        try:
            # Gemini doesn't have native batch API, so we'll call individually
            # This is less efficient but works
            embeddings = []
            for text in texts:
                result = self._gemini_client.embed_content(
                    model=self.settings.gemini_embedding_model,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(result['embedding'])
            logger.debug(f"Generated {len(embeddings)} Gemini embeddings")
            return embeddings
        except Exception as e:
            logger.error(f"Gemini batch embedding failed: {e}")
            raise  # No fallback - fail explicitly

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

        # Return based on provider
        if self._provider == "openai":
            return 1536  # OpenAI text-embedding-3-small
        elif self._provider == "gemini":
            return 768  # Gemini text-embedding-004
        else:  # local
            # Local model dimension (384 for MiniLM, but detect if possible)
            if self._local_model is not None:
                try:
                    test_embed = self._local_model.encode("test", convert_to_numpy=True)
                    self._actual_dimension = len(test_embed)
                    return self._actual_dimension
                except Exception:
                    pass
            return 384  # Fallback default

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
