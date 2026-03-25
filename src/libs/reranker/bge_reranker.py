"""BGE Reranker implementation."""

from typing import Any, Dict, List, Optional

from src.libs.reranker.base_reranker import BaseReranker


class BGEReranker(BaseReranker):
    """BGE Reranker using cross-encoder model."""

    def __init__(self, model: str = "BAAI/bge-reranker-v2-m3"):
        """Initialize BGE Reranker.

        Args:
            model: Model name (default: BAAI/bge-reranker-v2-m3).
        """
        self.model = model
        self._client = None

    def _get_client(self):
        """Get or create the reranker client."""
        if self._client is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError:
                raise ImportError(
                    "sentence-transformers package is required for BGE Reranker. "
                    "Install it with: pip install sentence-transformers"
                )
            self._client = CrossEncoder(self.model)
        return self._client

    def rerank(
        self, query: str, candidates: List[Dict[str, Any]], **kwargs
    ) -> List[Dict[str, Any]]:
        """Rerank candidates using BGE cross-encoder.

        Args:
            query: The search query.
            candidates: List of candidate documents.
            **kwargs: Additional parameters (top_k, etc.)

        Returns:
            List of reranked candidates with updated scores.
        """
        top_k = kwargs.get("top_k", len(candidates))

        if not candidates:
            return []

        client = self._get_client()

        # Prepare pairs for cross-encoder
        pairs = [[query, c.get("text", c.get("content", ""))] for c in candidates]

        # Get scores
        scores = client.predict(pairs)

        # Add scores to candidates and sort
        scored_candidates = []
        for i, candidate in enumerate(candidates):
            scored_candidate = candidate.copy()
            scored_candidate["rerank_score"] = float(scores[i])
            scored_candidates.append(scored_candidate)

        # Sort by rerank_score descending
        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

        return scored_candidates[:top_k]

    def get_model_name(self) -> str:
        """Return the model name."""
        return self.model
