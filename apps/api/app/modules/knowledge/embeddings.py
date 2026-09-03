import hashlib
import math
import os
import re
from typing import Optional
import logging
from functools import lru_cache

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSIONS = 384

class EmbeddingProvider:
    """Factory for embedding providers with automatic fallback"""
    
    GEMINI = "gemini"
    LIGHTWEIGHT = "lightweight"
    
    def __init__(self, provider: str = None):
        self.provider = provider or os.getenv("EMBEDDING_PROVIDER", self.LIGHTWEIGHT)
        self._initialize_provider()
    
    def _initialize_provider(self):
        if self.provider == self.GEMINI:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.gemini_model = "models/embedding-001"
                self.dimensions = EMBEDDING_DIMENSIONS
                logger.info("Initialized Gemini embedding provider")
            else:
                logger.warning("GEMINI_API_KEY not set, falling back to lightweight embeddings")
                self.provider = self.LIGHTWEIGHT
                self.dimensions = EMBEDDING_DIMENSIONS
        else:
            self.dimensions = EMBEDDING_DIMENSIONS
    
    def embed_text(self, text: str) -> list[float]:
        """Embed text using configured provider"""
        if self.provider == self.GEMINI:
            return embed_with_gemini(text)
        return embed_with_lightweight(text)
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts efficiently"""
        if self.provider == self.GEMINI:
            return embed_batch_with_gemini(texts)
        return [embed_with_lightweight(text) for text in texts]


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((
        google_exceptions.ResourceExhausted,
        google_exceptions.ServiceUnavailable,
        google_exceptions.DeadlineExceeded,
    )),
)
def embed_with_gemini(text: str) -> list[float]:
    """
    Generate embeddings using Google's Gemini API.
    Includes retry logic for production reliability.
    """
    try:
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_document",
        )
        embedding = result["embedding"]
        if len(embedding) == EMBEDDING_DIMENSIONS:
            return embedding

        if len(embedding) % EMBEDDING_DIMENSIONS != 0:
            raise ValueError(
                f"Gemini returned {len(embedding)} dimensions; expected a multiple of {EMBEDDING_DIMENSIONS}."
            )

        scale = len(embedding) // EMBEDDING_DIMENSIONS
        return [
            sum(embedding[index * scale : (index + 1) * scale]) / scale
            for index in range(EMBEDDING_DIMENSIONS)
        ]
    except Exception as e:
        logger.error(f"Gemini embedding failed: {str(e)}")
        # Fallback to lightweight on failure
        logger.warning("Falling back to lightweight embedding")
        return embed_with_lightweight(text)


def embed_batch_with_gemini(texts: list[str]) -> list[list[float]]:
    """
    Batch embed multiple texts with Gemini for efficiency.
    """
    embeddings = []
    batch_size = int(os.getenv("GEMINI_BATCH_SIZE", "20"))
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            for text in batch:
                embedding = embed_with_gemini(text)
                embeddings.append(embedding)
        except Exception as e:
            logger.error(f"Batch embedding failed at index {i}: {str(e)}")
            # Fallback for remaining items
            for text in batch[len(embeddings)-i:]:
                embeddings.append(embed_with_lightweight(text))
    
    return embeddings


def tokenize(text: str) -> list[str]:
    """Extract meaningful tokens from text"""
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def stable_hash_token(token: str) -> int:
    """Create stable hash from token"""
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def embed_with_lightweight(text: str) -> list[float]:
    """
    Lightweight deterministic embedding for fallback/development.
    Not production-grade for semantic search but works without API.
    """
    vector = [0.0] * EMBEDDING_DIMENSIONS
    tokens = tokenize(text)

    if not tokens:
        return vector

    for token in tokens:
        hashed = stable_hash_token(token)
        index = hashed % EMBEDDING_DIMENSIONS
        sign = 1.0 if (hashed // EMBEDDING_DIMENSIONS) % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))

    if norm == 0:
        return vector

    return [value / norm for value in vector]


# Initialize global embedding provider
embedding_provider = EmbeddingProvider()

# Legacy compatibility functions
def embed_text(text: str) -> list[float]:
    """Main embedding function - uses configured provider"""
    return embedding_provider.embed_text(text)


def embed_texts_batch(texts: list[str]) -> list[list[float]]:
    """Batch embedding for multiple texts"""
    return embedding_provider.embed_batch(texts)