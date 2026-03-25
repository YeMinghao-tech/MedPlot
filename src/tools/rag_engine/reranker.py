"""Reranker integration for fine-grained relevance ranking."""

from typing import Any, Dict, List

from src.libs.reranker.base_reranker import BaseReranker
from src.tools.rag_engine.hybrid_search import RetrievalResult


class RAGReranker:
    """Reranker wrapper for RAG pipeline.

    Wraps a BaseReranker (typically BGE cross-encoder) to provide
    fine-grained relevance scoring for retrieval candidates.
    """

    def __init__(self, reranker: BaseReranker):
        """Initialize the RAG reranker.

        Args:
            reranker: A BaseReranker implementation (e.g., BGEReranker).
        """
        self.reranker = reranker

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

    def get_model_name(self) -> str:
        """Get the reranker model name.

        Returns:
            Model name string.
        """
        return self.reranker.get_model_name()
