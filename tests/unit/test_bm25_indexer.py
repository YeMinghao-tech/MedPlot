"""Tests for BM25 indexer."""

import tempfile

from src.core.types import Chunk
from src.ingestion.storage.bm25_indexer import BM25Indexer


class TestBM25Indexer:
    """Test BM25Indexer functionality."""

    def test_build_empty_corpus(self):
        """Test building index with empty corpus."""
        indexer = BM25Indexer()
        indexer.build([])
        assert indexer.corpus_size == 0

    def test_build_from_chunks(self):
        """Test building index from chunks."""
        indexer = BM25Indexer()
        chunks = [
            Chunk(chunk_id="c1", text="感冒是一种常见疾病", source_ref="doc1", chunk_index=0),
            Chunk(chunk_id="c2", text="发烧是感冒的症状之一", source_ref="doc1", chunk_index=1),
        ]

        indexer.build(chunks)

        assert indexer.corpus_size == 2
        assert len(indexer.chunk_ids) == 2
        assert "c1" in indexer.chunk_ids
        assert "c2" in indexer.chunk_ids

    def test_query_returns_results(self):
        """Test that query returns results."""
        indexer = BM25Indexer()
        chunks = [
            Chunk(chunk_id="c1", text="感冒是一种常见疾病", source_ref="doc1", chunk_index=0),
            Chunk(chunk_id="c2", text="发烧是感冒的症状", source_ref="doc1", chunk_index=1),
            Chunk(chunk_id="c3", text="心脏病需要及时治疗", source_ref="doc1", chunk_index=2),
        ]

        indexer.build(chunks)
        results = indexer.query("感冒", top_k=2)

        assert len(results) <= 2
        assert all(isinstance(r[0], str) for r in results)
        assert all(isinstance(r[1], float) for r in results)

    def test_query_empty_index(self):
        """Test query on empty index."""
        indexer = BM25Indexer()
        results = indexer.query("test")
        assert results == []

    def test_query_top_k(self):
        """Test that top_k is respected."""
        indexer = BM25Indexer()
        chunks = [
            Chunk(chunk_id=f"c{i}", text=f"文档{i}包含一些内容", source_ref="doc1", chunk_index=i)
            for i in range(10)
        ]

        indexer.build(chunks)
        results = indexer.query("文档", top_k=3)

        assert len(results) == 3

    def test_save_and_load(self):
        """Test saving and loading index."""
        indexer1 = BM25Indexer()
        chunks = [
            Chunk(chunk_id="c1", text="感冒是一种常见疾病", source_ref="doc1", chunk_index=0),
            Chunk(chunk_id="c2", text="发烧是感冒的症状", source_ref="doc1", chunk_index=1),
        ]
        indexer1.build(chunks)

        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            path = f.name

        try:
            indexer1.save(path)

            indexer2 = BM25Indexer()
            indexer2.load(path)

            assert indexer2.corpus_size == indexer1.corpus_size
            assert indexer2.chunk_ids == indexer1.chunk_ids

            # Query should return same results
            results1 = indexer1.query("感冒")
            results2 = indexer2.query("感冒")
            assert results1 == results2
        finally:
            import os
            os.unlink(path)

    def test_query_scores_ordered(self):
        """Test that query results are ordered by score descending."""
        indexer = BM25Indexer()
        chunks = [
            Chunk(chunk_id="c1", text="感冒是常见疾病", source_ref="doc1", chunk_index=0),
            Chunk(chunk_id="c2", text="感冒导致发烧", source_ref="doc1", chunk_index=1),
            Chunk(chunk_id="c3", text="心脏病是严重疾病", source_ref="doc1", chunk_index=2),
        ]

        indexer.build(chunks)
        results = indexer.query("感冒发烧")

        scores = [r[1] for r in results]
        assert scores == sorted(scores, reverse=True)
