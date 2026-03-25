"""Base Reranker interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseReranker(ABC):
    """Abstract base class for Reranker providers."""

    @abstractmethod
    def rerank(
        self, query: str, candidates: List[Dict[str, Any]], **kwargs
    ) -> List[Dict[str, Any]]:
        """Rerank candidate documents based on query.

        Args:
            query: The search query.
            candidates: List of candidate documents with 'id', 'text', and 'score'.
            **kwargs: Additional provider-specific parameters.

        Returns:
            List of reranked candidates with updated scores.
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model name."""
        pass
