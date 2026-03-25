"""Reranker integration for fine-grained relevance ranking."""

from typing import Any, Dict, List, Optional

from src.libs.reranker.base_reranker import BaseReranker
from src.tools.rag_engine.hybrid_search import RetrievalResult


class RAGReranker:
    """Reranker wrapper for RAG pipeline.

    Wraps a BaseReranker (typically BGE cross-encoder) to provide
    fine-grained relevance scoring for retrieval candidates.

    Includes H4: Circuit breaker - when max rerank score < threshold,
    falls back to original candidates without reranking.
    """

    # Default circuit breaker threshold
    DEFAULT_THRESHOLD = 0.7

    def __init__(
        self,
        reranker: BaseReranker,
        circuit_breaker_threshold: float = DEFAULT_THRESHOLD,
    ):
        """Initialize the RAG reranker.

        Args:
            reranker: A BaseReranker implementation (e.g., BGEReranker).
            circuit_breaker_threshold: Minimum score threshold for circuit breaker.
                                      If max rerank score is below this, skip reranking.
        """
        self.reranker = reranker
        self.circuit_breaker_threshold = circuit_breaker_threshold

    def rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: int = 10,
    ) -> List[RetrievalResult]:
        """Rerank retrieval candidates using cross-encoder.

        Args:
            query: The search query.
            candidates: List of RetrievalResult from hybrid search.
            top_k: Number of results to return after reranking.

        Returns:
            List of reranked RetrievalResult with updated scores.
            If circuit breaker triggers, returns original candidates.
        """
        if not candidates:
            return []

        # Convert RetrievalResult to reranker format
        reranker_candidates = [
            {
                "id": c.chunk_id,
                "text": c.text,
                "score": c.score,
            }
            for c in candidates
        ]

        # Rerank
        reranked = self.reranker.rerank(query, reranker_candidates)

        # H4: Circuit breaker - check max rerank score
        max_score = max(
            r.get("rerank_score", r.get("score", 0.0))
            for r in reranked
        )

        if max_score < self.circuit_breaker_threshold:
            # Circuit breaker triggered - return original candidates without reranking
            # Mark them as "fallback" source to indicate circuit breaker was triggered
            return [
                RetrievalResult(
                    chunk_id=c.chunk_id,
                    text=c.text,
                    score=c.score,
                    source="fallback",
                    metadata={**c.metadata, "circuit_breaker": True} if c.metadata else {"circuit_breaker": True},
                )
                for c in candidates[:top_k]
            ]

        # Convert back to RetrievalResult
        results = []
        for r in reranked:
            # Find original candidate to preserve metadata
            original = next(
                (c for c in candidates if c.chunk_id == r["id"]),
                None
            )
            if original:
                results.append(RetrievalResult(
                    chunk_id=r["id"],
                    text=r.get("text", original.text),
                    score=r.get("score", r.get("rerank_score", 0.0)),
                    source="reranked",
                    metadata=original.metadata,
                ))
            else:
                results.append(RetrievalResult(
                    chunk_id=r["id"],
                    text=r.get("text", ""),
                    score=r.get("score", r.get("rerank_score", 0.0)),
                    source="reranked",
                    metadata={},
                ))

        return results[:top_k]

    def rerank_with_fallback(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: int = 10,
        fallback_threshold: Optional[float] = None,
    ) -> tuple[List[RetrievalResult], bool]:
        """Rerank with explicit fallback indicator.

        Args:
            query: The search query.
            candidates: List of RetrievalResult from hybrid search.
            top_k: Number of results to return after reranking.
            fallback_threshold: Override circuit breaker threshold.

        Returns:
            Tuple of (results, used_fallback).
            used_fallback is True if circuit breaker triggered.
        """
        threshold = fallback_threshold or self.circuit_breaker_threshold

        if not candidates:
            return [], False

        # Convert RetrievalResult to reranker format
        reranker_candidates = [
            {
                "id": c.chunk_id,
                "text": c.text,
                "score": c.score,
            }
            for c in candidates
        ]

        # Rerank
        reranked = self.reranker.rerank(query, reranker_candidates)

        # Check max rerank score
        max_score = max(
            r.get("rerank_score", r.get("score", 0.0))
            for r in reranked
        )

        if max_score < threshold:
            # Circuit breaker triggered
            return [
                RetrievalResult(
                    chunk_id=c.chunk_id,
                    text=c.text,
                    score=c.score,
                    source="fallback",
                    metadata={**c.metadata, "circuit_breaker": True} if c.metadata else {"circuit_breaker": True},
                )
                for c in candidates[:top_k]
            ], True

        # Normal reranking
        results = []
        for r in reranked:
            original = next(
                (c for c in candidates if c.chunk_id == r["id"]),
                None
            )
            if original:
                results.append(RetrievalResult(
                    chunk_id=r["id"],
                    text=r.get("text", original.text),
                    score=r.get("score", r.get("rerank_score", 0.0)),
                    source="reranked",
                    metadata=original.metadata,
                ))
            else:
                results.append(RetrievalResult(
                    chunk_id=r["id"],
                    text=r.get("text", ""),
                    score=r.get("score", r.get("rerank_score", 0.0)),
                    source="reranked",
                    metadata={},
                ))

        return results[:top_k], False

    def get_model_name(self) -> str:
        """Get the reranker model name.

        Returns:
            Model name string.
        """
        return self.reranker.get_model_name()
