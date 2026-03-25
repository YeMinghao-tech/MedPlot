"""Tests for core data types."""

from datetime import datetime

import pytest

from src.core.types import Chunk, ChunkRecord, Document


class TestDocument:
    """Test Document dataclass."""

    def test_create_document(self):
        """Test creating a Document."""
        doc = Document(
            doc_id="doc1",
            text="This is a test document.",
            metadata={"source": "test"},
            source_ref="/path/to/doc.txt",
        )
        assert doc.doc_id == "doc1"
        assert doc.text == "This is a test document."
        assert doc.metadata["source"] == "test"
        assert doc.source_ref == "/path/to/doc.txt"
        assert isinstance(doc.created_at, datetime)

    def test_document_to_dict(self):
        """Test Document serialization."""
        doc = Document(doc_id="doc1", text="Test", source_ref="/path")
        data = doc.to_dict()
        assert data["doc_id"] == "doc1"
        assert data["text"] == "Test"
        assert "created_at" in data

    def test_document_from_dict(self):
        """Test Document deserialization."""
        data = {
            "doc_id": "doc1",
            "text": "Test",
            "metadata": {"key": "value"},
            "source_ref": "/path",
            "created_at": "2024-01-01T00:00:00",
        }
        doc = Document.from_dict(data)
        assert doc.doc_id == "doc1"
        assert doc.text == "Test"
        assert doc.metadata["key"] == "value"
        assert doc.source_ref == "/path"


class TestChunk:
    """Test Chunk dataclass."""

    def test_create_chunk(self):
        """Test creating a Chunk."""
        chunk = Chunk(
            chunk_id="chunk1",
            text="This is a chunk.",
            metadata={"section": "intro"},
            source_ref="doc1",
            chunk_index=0,
        )
        assert chunk.chunk_id == "chunk1"
        assert chunk.text == "This is a chunk."
        assert chunk.metadata["section"] == "intro"
        assert chunk.source_ref == "doc1"
        assert chunk.chunk_index == 0

    def test_chunk_to_dict(self):
        """Test Chunk serialization."""
        chunk = Chunk(chunk_id="chunk1", text="Test", source_ref="doc1", chunk_index=0)
        data = chunk.to_dict()
        assert data["chunk_id"] == "chunk1"
        assert data["text"] == "Test"
        assert data["chunk_index"] == 0

    def test_chunk_from_dict(self):
        """Test Chunk deserialization."""
        data = {
            "chunk_id": "chunk1",
            "text": "Test",
            "metadata": {"key": "value"},
            "source_ref": "doc1",
            "chunk_index": 2,
        }
        chunk = Chunk.from_dict(data)
        assert chunk.chunk_id == "chunk1"
        assert chunk.text == "Test"
        assert chunk.metadata["key"] == "value"
        assert chunk.chunk_index == 2


class TestChunkRecord:
    """Test ChunkRecord dataclass."""

    def test_create_chunk_record(self):
        """Test creating a ChunkRecord."""
        chunk = Chunk(
            chunk_id="chunk1",
            text="This is a chunk.",
            source_ref="doc1",
            chunk_index=0,
        )
        record = ChunkRecord(
            chunk=chunk,
            dense_embedding=[0.1, 0.2, 0.3],
            sparse_embedding={"term": 0.5},
            authority_level=3,
            disease_tags=["感冒", "发热"],
        )
        assert record.chunk.chunk_id == "chunk1"
        assert record.dense_embedding == [0.1, 0.2, 0.3]
        assert record.authority_level == 3
        assert "感冒" in record.disease_tags

    def test_chunk_record_to_dict(self):
        """Test ChunkRecord serialization."""
        chunk = Chunk(chunk_id="chunk1", text="Test", source_ref="doc1", chunk_index=0)
        record = ChunkRecord(
            chunk=chunk,
            dense_embedding=[0.1, 0.2],
            authority_level=2,
            disease_tags=["咳嗽"],
        )
        data = record.to_dict()
        assert data["chunk_id"] == "chunk1"
        assert data["dense_embedding"] == [0.1, 0.2]
        assert data["authority_level"] == 2
        assert "咳嗽" in data["disease_tags"]

    def test_chunk_record_from_dict(self):
        """Test ChunkRecord deserialization."""
        data = {
            "chunk_id": "chunk1",
            "text": "Test",
            "metadata": {},
            "source_ref": "doc1",
            "chunk_index": 0,
            "dense_embedding": [0.1, 0.2],
            "sparse_embedding": {"term": 0.5},
            "authority_level": 3,
            "disease_tags": ["发烧"],
            "image_refs": [],
            "has_unprocessed_images": False,
        }
        record = ChunkRecord.from_dict(data)
        assert record.chunk.chunk_id == "chunk1"
        assert record.dense_embedding == [0.1, 0.2]
        assert record.authority_level == 3

    def test_chunk_record_to_vector_record(self):
        """Test conversion to vector store record format."""
        chunk = Chunk(chunk_id="chunk1", text="Test content", source_ref="doc1", chunk_index=0)
        record = ChunkRecord(
            chunk=chunk,
            dense_embedding=[0.1, 0.2, 0.3],
            authority_level=4,
            disease_tags=["肺炎"],
        )
        vec_record = record.to_vector_record()
        assert vec_record["id"] == "chunk1"
        assert vec_record["text"] == "Test content"
        assert vec_record["embedding"] == [0.1, 0.2, 0.3]
        assert vec_record["metadata"]["authority_level"] == 4
        assert "肺炎" in vec_record["metadata"]["disease_tags"]

    def test_chunk_record_default_values(self):
        """Test ChunkRecord default field values."""
        chunk = Chunk(chunk_id="chunk1", text="Test")
        record = ChunkRecord(chunk=chunk)
        assert record.dense_embedding == []
        assert record.sparse_embedding == {}
        assert record.authority_level == 1
        assert record.disease_tags == []
        assert record.image_refs == []
        assert record.has_unprocessed_images is False
