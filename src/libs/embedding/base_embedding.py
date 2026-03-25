"""Base Embedding interface."""

from abc import ABC, abstractmethod
from typing import List


class BaseEmbedding(ABC):
    """Abstract base class for Embedding providers."""

    @abstractmethod
    def embed(self, texts: List[str], **kwargs) -> List[List[float]]:
        """Generate embeddings for texts.

        Args:
            texts: List of text strings to embed.
            **kwargs: Additional provider-specific parameters.

        Returns:
            List of embedding vectors, one per input text.
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model name."""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Return the embedding dimension."""
        pass
