"""Turn text into embeddings: lists of numbers where similar meanings are close together.

Two embedders share the same interface:
  - FastEmbedEmbedder: a real AI model (BAAI/bge-small-en-v1.5, runs on your CPU).
    Downloaded automatically the first time it's used.
  - FakeEmbedder: a tiny word-counting stand-in for tests. Instant, no download,
    and always gives the same numbers for the same text.

Set the EMBEDDER environment variable to "fake" to use the stand-in.
"""

import hashlib
import math
import os
import re
from functools import lru_cache

EMBEDDING_DIM = 384  # bge-small-en-v1.5 produces 384 numbers per text


class FastEmbedEmbedder:
    MODEL_NAME = "BAAI/bge-small-en-v1.5"

    def __init__(self) -> None:
        from fastembed import TextEmbedding  # imported here so tests never load it

        self.model = TextEmbedding(model_name=self.MODEL_NAME)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self.model.embed(texts)]


class FakeEmbedder:
    """Each word switches on one of the 384 positions, so texts sharing words are 'similar'."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIM
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            position = int(hashlib.md5(word.encode()).hexdigest(), 16) % EMBEDDING_DIM
            vector[position] += 1.0
        if not any(vector):
            vector[0] = 1.0  # avoid an all-zero vector, which has no direction
        length = math.sqrt(sum(v * v for v in vector))
        return [v / length for v in vector]


@lru_cache  # load the model only once per process
def get_embedder():
    if os.getenv("EMBEDDER", "fastembed") == "fake":
        return FakeEmbedder()
    return FastEmbedEmbedder()
