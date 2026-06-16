import hashlib
import math
import re


EMBEDDING_DIMENSIONS = 384


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def stable_hash_token(token: str) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def embed_text(text: str) -> list[float]:
    """
    Lightweight deterministic embedding.

    This is not as smart as Gemini/OpenAI embeddings, but it is enough for Phase 6:
    - stable
    - offline
    - no API key needed
    - works with pgvector
    - replaceable later
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