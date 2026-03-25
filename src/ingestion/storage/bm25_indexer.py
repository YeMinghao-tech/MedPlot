"""BM25 indexer for building and querying inverted indexes."""

import json
import math
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.types import Chunk
from src.ingestion.embedding.sparse_encoder import SparseEncoder


class BM25Indexer:
    """BM25 inverted index for sparse retrieval.

    Supports building index from chunks and querying with new queries.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """Initialize BM25 indexer.

        Args:
            k1: Term frequency saturation parameter.
            b: Length normalization parameter.
        """
        self.k1 = k1
        self.b = b
        self.encoder = SparseEncoder()
        self.corpus_size = 0
        self.doc_lengths: List[int] = []
        self.avg_doc_length = 0.0
        self.doc_vectors: List[Dict[str, float]] = []
        self.chunk_ids: List[str] = []
        self.chunk_refs: List[str] = []

    def build(self, chunks: List[Chunk]) -> None:
        """Build BM25 index from chunks.

        Args:
            chunks: List of chunks to index.
        """
        if not chunks:
            return

        self.corpus_size = len(chunks)
        self.doc_lengths = []
        self.doc_vectors = []
        self.chunk_ids = []
        self.chunk_refs = []

        # Encode all chunks to get sparse vectors
        sparse_vectors = self.encoder.encode(chunks)

        for i, chunk in enumerate(chunks):
            self.chunk_ids.append(chunk.chunk_id)
            self.chunk_refs.append(chunk.source_ref or "")
            self.doc_vectors.append(sparse_vectors[i])
            self.doc_lengths.append(len(chunk.text))

        self.avg_doc_length = sum(self.doc_lengths) / self.corpus_size if self.corpus_size > 0 else 0

    def query(self, query_text: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Query the BM25 index.

        Args:
            query_text: Query text.
            top_k: Number of results to return.

        Returns:
            List of (chunk_id, score) tuples.
        """
        if not self.doc_vectors:
            return []

        # Encode query
        query_vector = self.encoder.encode_single(
            Chunk(chunk_id="", text=query_text, source_ref="", chunk_index=0)
        )

        # Score all documents
        scores = []
        for i, doc_vector in enumerate(self.doc_vectors):
            score = self._compute_bm25_score(query_vector, doc_vector, self.doc_lengths[i])
            scores.append((self.chunk_ids[i], score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:top_k]

    def _compute_bm25_score(
        self,
        query_vector: Dict[str, float],
        doc_vector: Dict[str, float],
        doc_length: int,
    ) -> float:
        """Compute BM25 score for a document.

        Args:
            query_vector: Query sparse vector.
            doc_vector: Document sparse vector.
            doc_length: Document length.

        Returns:
            BM25 score.
        """
        score = 0.0

        for term, query_weight in query_vector.items():
            if term in doc_vector:
                doc_weight = doc_vector[term]
                # BM25 scoring formula
                numerator = query_weight * (self.k1 + 1)
                denominator = query_weight + self.k1 * (
                    1 - self.b + self.b * doc_length / self.avg_doc_length
                )
                score += numerator / denominator if denominator != 0 else 0

        return score

    def save(self, path: str) -> None:
        """Save index to file.

        Args:
            path: Path to save the index.
        """
        data = {
            "k1": self.k1,
            "b": self.b,
            "corpus_size": self.corpus_size,
            "doc_lengths": self.doc_lengths,
            "avg_doc_length": self.avg_doc_length,
            "doc_vectors": self.doc_vectors,
            "chunk_ids": self.chunk_ids,
            "chunk_refs": self.chunk_refs,
        }

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(data, f)

    def load(self, path: str) -> None:
        """Load index from file.

        Args:
            path: Path to load the index from.
        """
        with open(path, "rb") as f:
            data = pickle.load(f)

        self.k1 = data["k1"]
        self.b = data["b"]
        self.corpus_size = data["corpus_size"]
        self.doc_lengths = data["doc_lengths"]
        self.avg_doc_length = data["avg_doc_length"]
        self.doc_vectors = data["doc_vectors"]
        self.chunk_ids = data["chunk_ids"]
        self.chunk_refs = data["chunk_refs"]
        # Re-initialize encoder with loaded corpus
        self.encoder = SparseEncoder()
        # Update encoder stats
        self.encoder.corpus_size = self.corpus_size
        self.encoder.doc_freqs = {}
        for doc_vec in self.doc_vectors:
            for term in doc_vec.keys():
                self.encoder.doc_freqs[term] = self.encoder.doc_freqs.get(term, 0) + 1
        self.encoder.idf_cache = {
            term: self.encoder._compute_idf(df)
            for term, df in self.encoder.doc_freqs.items()
        }
