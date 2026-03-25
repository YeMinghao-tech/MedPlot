"""None Reranker - returns candidates unchanged."""

from typing import Any, Dict, List

from src.libs.reranker.base_reranker import BaseReranker


class NoneReranker(BaseReranker):
    """No-op reranker that returns candidates in original order."""

    def __init__(self):
        pass

    def rerank(
        self, query: str, candidates: List[Dict[str, Any]], **kwargs
    ) -> List[Dict[str, Any]]:
        """Return candidates unchanged.

        Args:
            query: The search query (unused).
            candidates: List of candidate documents.
            **kwargs: Additional parameters.

        Returns:
            List of candidates with original scores.
        """
        top_k = kwargs.get("top_k", len(candidates))
        return candidates[:top_k]

    def get_model_name(self) -> str:
        """Return the model name."""
        return "none"
