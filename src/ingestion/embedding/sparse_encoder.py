"""Sparse encoder for generating sparse vectors (BM25-style)."""

import math
import re
from collections import Counter
from typing import Any, Dict, List, Set, Tuple

from src.core.types import Chunk


class SparseEncoder:
    """Encodes chunks into sparse vectors for BM25-style retrieval.

    Uses term frequency (TF) with inverse document frequency (IDF) weighting.
    """

    # Chinese word boundary pattern (simple tokenizer)
    # Matches: 1) consecutive Chinese chars 2) consecutive alphanumeric
    TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fa5]+|[a-zA-Z0-9_]+")

    def __init__(self):
        """Initialize the sparse encoder."""
        self.corpus_size = 0
        self.doc_freqs: Dict[str, int] = {}  # Document frequency for each term
        self.idf_cache: Dict[str, float] = {}  # Cached IDF values

    def encode(self, chunks: List[Chunk]) -> List[Dict[str, float]]:
        """Encode chunks into sparse vectors.

        Args:
            chunks: List of chunks to encode.

        Returns:
            List of sparse vectors (term -> score), one per chunk.
        """
        if not chunks:
            return []

        texts = [chunk.text for chunk in chunks]

        # Update corpus statistics
        self._update_stats(texts)

        # Encode each document
        sparse_vectors = []
        for text in texts:
            vector = self._compute_sparse_vector(text)
            sparse_vectors.append(vector)

        return sparse_vectors

    def encode_single(self, chunk: Chunk) -> Dict[str, float]:
        """Encode a single chunk.

        Args:
            chunk: Chunk to encode.

        Returns:
            Sparse vector.
        """
        return self._compute_sparse_vector(chunk.text)

    def _update_stats(self, texts: List[str]) -> None:
        """Update corpus statistics for IDF calculation.

        Args:
            texts: List of texts in the corpus.
        """
        self.corpus_size = len(texts)
        doc_freqs: Dict[str, int] = Counter()

        for text in texts:
            terms = self._tokenize(text)
            unique_terms = set(terms)
            for term in unique_terms:
                doc_freqs[term] += 1

        self.doc_freqs = dict(doc_freqs)

        # Precompute IDF for all terms
        for term, df in self.doc_freqs.items():
            self.idf_cache[term] = self._compute_idf(df)

    def _compute_idf(self, doc_freq: int) -> float:
        """Compute IDF for a term.

        Args:
            doc_freq: Document frequency.

        Returns:
            IDF score.
        """
        # Smoothed IDF formula
        return math.log((self.corpus_size - doc_freq + 0.5) / (doc_freq + 0.5) + 1)

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into terms.

        Args:
            text: Input text.

        Returns:
            List of tokens.
        """
        # Extract Chinese characters and English words
        tokens = self.TOKEN_PATTERN.findall(text.lower())
        # Filter out single characters and very long terms
        return [t for t in tokens if 1 < len(t) < 50]

    def _compute_sparse_vector(self, text: str) -> Dict[str, float]:
        """Compute sparse vector for a document.

        Args:
            text: Document text.

        Returns:
            Dict mapping term to BM25 score.
        """
        terms = self._tokenize(text)
        term_freqs = Counter(terms)

        # Compute TF with length normalization
        doc_len = len(terms)
        if doc_len == 0:
            return {}

        vector = {}
        for term, tf in term_freqs.items():
            # TF component (log normalization + 1)
            tf_score = 1 + math.log(tf)
            # IDF component
            idf = self.idf_cache.get(term, 0)
            # BM25 score
            vector[term] = tf_score * idf

        return vector
