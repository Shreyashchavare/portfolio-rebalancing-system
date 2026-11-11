"""Embedding generation services supporting local ONNX models and deterministic test fakes."""

from abc import ABC, abstractmethod
import hashlib
import os
from typing import Any, List, Optional
import numpy as np


class EmbeddingModelError(Exception):
    """Raised when an embedding model fails to initialize or generate embeddings."""

    pass


class BaseEmbeddingService(ABC):
    """Abstract interface for text embedding generation."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding vector dimension."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the identifier of the embedding model."""
        pass

    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate normalized embedding vectors for a batch of strings."""
        pass

    def generate_embedding(self, text: str) -> List[float]:
        """Generate a normalized embedding vector for a single string."""
        results = self.generate_embeddings([text])
        if not results:
            raise EmbeddingModelError("No embedding vector returned.")
        return results[0]


class FakeEmbeddingService(BaseEmbeddingService):
    """Deterministic, offline embedding service for unit testing without downloading models."""

    def __init__(self, dimension: int = 384, model_name: str = "fake-embedding-model") -> None:
        self._dimension = dimension
        self._model_name = model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Deterministically project each string into a normalized unit sphere vector."""
        vectors: List[List[float]] = []
        for text in texts:
            if not text or not text.strip():
                raise ValueError("Text cannot be empty or whitespace.")

            # Compute stable 32-bit integer seed from text SHA-256
            hasher = hashlib.sha256(text.strip().encode("utf-8"))
            seed = int.from_bytes(hasher.digest()[:4], "big")
            rng = np.random.RandomState(seed)

            # Generate random normal vector
            raw_vec = rng.randn(self._dimension).astype(np.float32)

            # L2 normalize
            norm = np.linalg.norm(raw_vec)
            if norm > 0:
                norm_vec = raw_vec / norm
            else:
                norm_vec = raw_vec

            vectors.append(norm_vec.tolist())

        return vectors


class EmbeddingService(BaseEmbeddingService):
    """Local embedding service powered by fastembed with quantized ONNX models."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        cache_dir: Optional[str] = None,
    ) -> None:
        self._model_name = model_name
        self._cache_dir = cache_dir
        self._model: Optional[Any] = None
        self._dimension = 384  # Standard dimension for BAAI/bge-small-en-v1.5 and all-MiniLM-L6-v2

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def _get_model(self) -> Any:
        """Lazily initialize the underlying fastembed model on first use."""
        if self._model is None:
            try:
                # Suppress Windows symlinks warning from huggingface_hub
                os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
                from fastembed import TextEmbedding

                self._model = TextEmbedding(
                    model_name=self._model_name,
                    cache_dir=self._cache_dir,
                )
            except Exception as err:
                raise EmbeddingModelError(
                    f"Failed to initialize local embedding model '{self._model_name}': {err}"
                ) from err
        return self._model

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate normalized embedding vectors using the local ONNX model.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of 384-dimensional normalized float vectors.

        Raises:
            ValueError: If any text string is empty.
            EmbeddingModelError: If model inference fails or produces invalid values.
        """
        for t in texts:
            if not t or not t.strip():
                raise ValueError("Text cannot be empty or whitespace.")

        model = self._get_model()
        try:
            raw_embeddings = list(model.embed(texts))
        except Exception as err:
            raise EmbeddingModelError(f"Embedding inference failed: {err}") from err

        results: List[List[float]] = []
        for emb in raw_embeddings:
            arr = np.asarray(emb, dtype=np.float32)

            # Dimensionality check
            if len(arr) != self._dimension:
                self._dimension = len(arr)

            # Non-finite check
            if np.isnan(arr).any() or np.isinf(arr).any():
                raise EmbeddingModelError("Embedding vector contains non-finite values (NaN or Inf).")

            # Ensure unit L2 normalization
            norm = np.linalg.norm(arr)
            if norm > 0:
                arr = arr / norm

            results.append(arr.tolist())

        return results

