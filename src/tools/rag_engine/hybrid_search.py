"""Hybrid search combining dense and sparse retrieval with RRF fusion."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from src.libs.embedding.base_embedding import BaseEmbedding
from src.libs.vector_store.base_vector_store import BaseVectorStore


@dataclass
class RetrievalResult:
    """A single retrieval result."""

    chunk_id: str
    text: str
    score: float
    source: str  # "dense", "sparse", or "fused"
    metadata: Dict[str, Any]


class HybridSearch:
    """Hybrid search combining dense (vector) and sparse (BM25) retrieval.

    Uses Reciprocal Rank Fusion (RRF) to combine results from both approaches.
    """

    def __init__(
        self,
        vector_store: BaseVectorStore,
        embedding_client: BaseEmbedding,
        bm25_indexer: Any = None,  # BM25Indexer type
        rrf_k: int = 60,
    ):
        """Initialize hybrid search.

        Args:
            vector_store: Vector store for dense retrieval.
            embedding_client: Embedding client for query encoding.
            bm25_indexer: BM25 indexer for sparse retrieval.
            rrf_k: RRF ranking constant (default 60).
        """
        self.vector_store = vector_store
        self.embedding_client = embedding_client
        self.bm25_indexer = bm25_indexer
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        top_k: int = 10,
        dense_top_k: int = 20,
        sparse_top_k: int = 20,
        collection: str = "default",
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """Execute hybrid search.

        Args:
            query: Search query.
            top_k: Final number of results to return.
            dense_top_k: Number of results to fetch from dense retrieval.
            sparse_top_k: Number of results to fetch from sparse retrieval.
            collection: Collection name.
            filters: Metadata filters.

        Returns:
            List of RetrievalResult sorted by fused score.
        """
        dense_results: List[Tuple[str, float]] = []
        sparse_results: List[Tuple[str, float]] = []

        # Dense retrieval
        dense_results = self._dense_search(
            query, dense_top_k, collection, filters
        )

        # Sparse retrieval (if BM25 indexer available)
        if self.bm25_indexer is not None:
            sparse_results = self._sparse_search(query, sparse_top_k)

        # Fuse results using RRF
        fused = self._rrf_fuse(dense_results, sparse_results, top_k)

        # Build final results with text
        return self._build_results(fused, collection)

    def _dense_search(
        self,
        query: str,
        top_k: int,
        collection: str,
        filters: Optional[Dict[str, Any]],
    ) -> List[Tuple[str, float]]:
        """Execute dense (vector) search.

        Args:
            query: Search query.
            top_k: Number of results.
            collection: Collection name.
            filters: Metadata filters.

        Returns:
            List of (chunk_id, score) tuples.
        """
        # Encode query
        query_embedding = self.embedding_client.embed([query])[0]

        # Query vector store
        raw_results = self.vector_store.query(
            vector=query_embedding,
            top_k=top_k,
            filters=filters,
            collection=collection,
        )

        # Normalize scores to 0-1 range (cosine similarity already normalized)
        results = []
        for r in raw_results:
            chunk_id = r.get("id", "")
            score = 1.0 - r.get("score", 1.0)  # Chroma returns distance, convert to similarity
            results.append((chunk_id, score))

        return results

    def _sparse_search(
        self,
        query: str,
        top_k: int,
    ) -> List[Tuple[str, float]]:
        """Execute sparse (BM25) search.

        Args:
            query: Search query.
            top_k: Number of results.

        Returns:
            List of (chunk_id, score) tuples.
        """
        if self.bm25_indexer is None:
            return []

        raw_results = self.bm25_indexer.query(query, top_k=top_k)
        return raw_results

    def _rrf_fuse(
        self,
        dense_results: List[Tuple[str, float]],
        sparse_results: List[Tuple[str, float]],
        top_k: int,
    ) -> List[Tuple[str, float, str]]:
        """Fuse results using Reciprocal Rank Fusion (RRF).

        RRF formula: score = sum(1 / (k + rank)), where k=60

        Args:
            dense_results: Dense retrieval results (chunk_id, score).
            sparse_results: Sparse retrieval results (chunk_id, score).
            top_k: Number of final results.

        Returns:
            List of (chunk_id, fused_score, source) tuples.
        """
        rrf_scores: Dict[str, float] = {}

        # Process dense results
        for rank, (chunk_id, score) in enumerate(dense_results):
            rrf = 1.0 / (self.rrf_k + rank + 1)
            if chunk_id not in rrf_scores:
                rrf_scores[chunk_id] = {"dense": 0.0, "sparse": 0.0, "max_raw": 0.0}
            rrf_scores[chunk_id]["dense"] = rrf
            rrf_scores[chunk_id]["max_raw"] = max(rrf_scores[chunk_id]["max_raw"], score)

        # Process sparse results
        for rank, (chunk_id, score) in enumerate(sparse_results):
            rrf = 1.0 / (self.rrf_k + rank + 1)
            if chunk_id not in rrf_scores:
                rrf_scores[chunk_id] = {"dense": 0.0, "sparse": 0.0, "max_raw": 0.0}
            rrf_scores[chunk_id]["sparse"] = rrf
            rrf_scores[chunk_id]["max_raw"] = max(rrf_scores[chunk_id]["max_raw"], score)

        # Compute fused scores
        fused = []
        for chunk_id, scores in rrf_scores.items():
            # Combined RRF score weighted by raw scores
            fused_score = (scores["dense"] + scores["sparse"]) * scores["max_raw"]
            source = "fused"
            if scores["dense"] > 0 and scores["sparse"] > 0:
                source = "fused"
            elif scores["dense"] > 0:
                source = "dense"
            else:
                source = "sparse"

            fused.append((chunk_id, fused_score, source))

        # Sort by fused score descending
        fused.sort(key=lambda x: x[1], reverse=True)

        return fused[:top_k]

    def _build_results(
        self,
        fused: List[Tuple[str, float, str]],
        collection: str,
    ) -> List[RetrievalResult]:
        """Build RetrievalResult objects from fused results.

        Args:
            fused: Fused results (chunk_id, score, source).
            collection: Collection name.

        Returns:
            List of RetrievalResult.
        """
        if not fused:
            return []

        # Get chunk_ids
        chunk_ids = [r[0] for r in fused]

        # Fetch full records from vector store
        records = self.vector_store.get_by_ids(chunk_ids, collection=collection)

        # Build lookup
        record_map = {r["id"]: r for r in records}

        results = []
        for chunk_id, score, source in fused:
            record = record_map.get(chunk_id, {})
            results.append(RetrievalResult(
                chunk_id=chunk_id,
                text=record.get("text", ""),
                score=score,
                source=source,
                metadata=record.get("metadata", {}),
            ))

        return results
