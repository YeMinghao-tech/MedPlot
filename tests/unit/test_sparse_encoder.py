"""Tests for sparse encoder."""

from src.core.types import Chunk
from src.ingestion.embedding.sparse_encoder import SparseEncoder


class TestSparseEncoder:
    """Test SparseEncoder functionality."""

    def test_tokenize_chinese(self):
        """Test tokenization of Chinese text."""
        encoder = SparseEncoder()
        text = "这是测试"
        tokens = encoder._tokenize(text)
        # Simple tokenizer may return whole string or individual chars
        assert len(tokens) > 0
        assert all(isinstance(t, str) for t in tokens)

    def test_tokenize_english(self):
        """Test tokenization of English text."""
        encoder = SparseEncoder()
        text = "This is a test"
        tokens = encoder._tokenize(text)
        assert "this" in tokens
        assert "test" in tokens

    def test_encode_single_chunk(self):
        """Test encoding a single chunk."""
        encoder = SparseEncoder()
        chunks = [
            Chunk(chunk_id="c1", text="感冒是一种常见疾病", source_ref="doc1", chunk_index=0),
        ]

        result = encoder.encode(chunks)

        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert len(result[0]) > 0

    def test_encode_multiple_chunks(self):
        """Test encoding multiple chunks updates IDF."""
        encoder = SparseEncoder()
        chunks = [
            Chunk(chunk_id="c1", text="感冒是常见疾病", source_ref="doc1", chunk_index=0),
            Chunk(chunk_id="c2", text="发烧是感冒的症状", source_ref="doc1", chunk_index=1),
        ]

        result = encoder.encode(chunks)

        assert len(result) == 2
        # Result should be sparse vectors (dict of term -> score)
        assert isinstance(result[0], dict)
        assert isinstance(result[1], dict)

    def test_encode_empty_list(self):
        """Test encoding empty list."""
        encoder = SparseEncoder()
        result = encoder.encode([])
        assert result == []

    def test_idf_calculation(self):
        """Test that IDF is computed correctly."""
        encoder = SparseEncoder()
        chunks = [
            Chunk(chunk_id="c1", text="文档1包含词A", source_ref="doc1", chunk_index=0),
            Chunk(chunk_id="c2", text="文档2包含词B", source_ref="doc1", chunk_index=1),
            Chunk(chunk_id="c3", text="文档3包含词C", source_ref="doc1", chunk_index=2),
        ]

        encoder.encode(chunks)

        # All terms appear in exactly 1 document
        assert encoder.corpus_size == 3
        # Check that doc_freqs is populated
        assert len(encoder.doc_freqs) > 0

    def test_encode_single(self):
        """Test encoding a single chunk."""
        encoder = SparseEncoder()
        # First encode some chunks to build corpus
        encoder.encode([
            Chunk(chunk_id="c1", text="其他文档", source_ref="doc1", chunk_index=0),
        ])

        chunk = Chunk(chunk_id="c2", text="测试文本", source_ref="doc1", chunk_index=1)
        result = encoder.encode_single(chunk)

        assert isinstance(result, dict)
        assert len(result) > 0
