"""LLM Reranker implementation."""

from typing import Any, Dict, List

from src.libs.reranker.base_reranker import BaseReranker


class LLMReranker(BaseReranker):
    """LLM-based Reranker using an LLM to score relevance."""

    def __init__(self, llm):
        """Initialize LLM Reranker.

        Args:
            llm: An LLM instance (BaseLLM subclass).
        """
        self.llm = llm

    def rerank(
        self, query: str, candidates: List[Dict[str, Any]], **kwargs
    ) -> List[Dict[str, Any]]:
        """Rerank candidates using LLM.

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

        scored_candidates = []
        for candidate in candidates:
            text = candidate.get("text", candidate.get("content", ""))
            score = self._llm_score(query, text)
            scored_candidate = candidate.copy()
            scored_candidate["rerank_score"] = score
            scored_candidates.append(scored_candidate)

        # Sort by rerank_score descending
        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

        return scored_candidates[:top_k]

    def _llm_score(self, query: str, text: str) -> float:
        """Use LLM to score relevance between query and text."""
        prompt = f"""Query: {query}
Document: {text}

Rate the relevance of the document to the query on a scale of 0 to 1.
Only respond with a number between 0 and 1."""

        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            # Try to parse the score from response
            import re

            match = re.search(r"0?\.\d+|1\.0|1", response.strip())
            if match:
                return float(match.group())
        except Exception:
            pass
        return 0.5  # Default score if parsing fails

    def get_model_name(self) -> str:
        """Return the model name."""
        return f"llm-{self.llm.get_model_name()}"
