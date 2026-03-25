"""Tests for dense encoder."""

from unittest.mock import MagicMock

from src.core.types import Chunk
from src.ingestion.embedding.dense_encoder import DenseEncoder


class TestDenseEncoder:
    """Test DenseEncoder functionality."""

    def test_encode_single_chunk(self):
        """Test encoding a single chunk."""
        # Create mock embedding client
        mock_embedding = MagicMock()
        mock_embedding.embed.return_value = [[0.1, 0.2, 0.3]]

        encoder = DenseEncoder(embedding_client=mock_embedding)
        chunk = Chunk(chunk_id="c1", text="test text", source_ref="doc1", chunk_index=0)

        result = encoder.encode_single(chunk)

        assert result == [0.1, 0.2, 0.3]
        mock_embedding.embed.assert_called_once_with(["test text"])

    def test_encode_multiple_chunks(self):
        """Test encoding multiple chunks."""
        mock_embedding = MagicMock()
        mock_embedding.embed.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ]

        encoder = DenseEncoder(embedding_client=mock_embedding)
        chunks = [
            Chunk(chunk_id="c1", text="text1", source_ref="doc1", chunk_index=0),
            Chunk(chunk_id="c2", text="text2", source_ref="doc1", chunk_index=1),
        ]

        result = encoder.encode(chunks)

        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]

    def test_encode_empty_list(self):
        """Test encoding empty list."""
        mock_embedding = MagicMock()
        encoder = DenseEncoder(embedding_client=mock_embedding)

        result = encoder.encode([])

        assert result == []
        mock_embedding.embed.assert_not_called()
