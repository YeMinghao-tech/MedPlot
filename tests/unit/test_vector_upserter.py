"""Tests for vector upsert."""

from unittest.mock import MagicMock

from src.core.types import Chunk, ChunkRecord
from src.ingestion.storage.vector_upserter import VectorUpserter


class FakeVectorStore:
    """Fake vector store for testing."""

    def __init__(self):
        self.upserted = []

    def upsert(self, records, collection="default"):
        self.upserted.extend(records)


class TestVectorUpserter:
    """Test VectorUpserter functionality."""

    def test_upsert_chunks(self):
        """Test upserting chunks to vector store."""
        fake_store = FakeVectorStore()
        upsert = VectorUpserter(vector_store=fake_store)

        chunks = [
            Chunk(chunk_id="c1", text="test text 1", source_ref="doc1", chunk_index=0),
            Chunk(chunk_id="c2", text="test text 2", source_ref="doc1", chunk_index=1),
        ]
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

        chunk_ids = upsert.upsert(chunks, embeddings)

        assert len(chunk_ids) == 2
        assert len(fake_store.upserted) == 2
        assert fake_store.upserted[0]["text"] == "test text 1"
        assert fake_store.upserted[1]["text"] == "test text 2"

    def test_upsert_empty_list(self):
        """Test upserting empty list."""
        upsert = VectorUpserter(vector_store=FakeVectorStore())
        chunk_ids = upsert.upsert([], [])
        assert chunk_ids == []

    def test_upsert_mismatched_lengths(self):
        """Test that mismatched chunk/embedding lengths raise error."""
        upsert = VectorUpserter(vector_store=FakeVectorStore())
        chunks = [
            Chunk(chunk_id="c1", text="text", source_ref="doc1", chunk_index=0),
        ]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]  # 2 embeddings for 1 chunk

        with MagicMock():
            try:
                upsert.upsert(chunks, embeddings)
                assert False, "Should have raised ValueError"
            except ValueError as e:
                assert "must match" in str(e)

    def test_generate_stable_id(self):
        """Test stable ID generation."""
        upsert = VectorUpserter(vector_store=FakeVectorStore())
        chunk = Chunk(chunk_id="c1", text="test text", source_ref="doc1", chunk_index=0)
        embedding = [0.1, 0.2, 0.3]

        id1 = upsert._generate_stable_id(chunk, embedding)
        id2 = upsert._generate_stable_id(chunk, embedding)

        # Same content + embedding should produce same ID
        assert id1 == id2
        assert id1.startswith("chunk_")

    def test_upsert_records(self):
        """Test upserting ChunkRecords."""
        fake_store = FakeVectorStore()
        upsert = VectorUpserter(vector_store=fake_store)

        chunk = Chunk(chunk_id="c1", text="test text", source_ref="doc1", chunk_index=0)
        record = ChunkRecord(
            chunk=chunk,
            dense_embedding=[0.1, 0.2, 0.3],
        )

        chunk_ids = upsert.upsert_records([record])

        assert len(chunk_ids) == 1
        assert chunk_ids[0] == "c1"
        assert len(fake_store.upserted) == 1

    def test_upsert_records_empty(self):
        """Test upserting empty ChunkRecords list."""
        upsert = VectorUpserter(vector_store=FakeVectorStore())
        chunk_ids = upsert.upsert_records([])
        assert chunk_ids == []
