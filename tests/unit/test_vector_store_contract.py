"""Tests for VectorStore Factory and contract."""

import pytest

from src.core.settings import Settings
from src.libs.vector_store.base_vector_store import BaseVectorStore
from src.libs.vector_store.chroma_store import ChromaStore
from src.libs.vector_store.vector_store_factory import VectorStoreFactory


class FakeVectorStore(BaseVectorStore):
    """Fake VectorStore for testing."""

    def __init__(self):
        self._data = {}

    def upsert(self, records, collection="default", **kwargs):
        for r in records:
            key = (r["id"], collection)
            self._data[key] = r

    def query(self, vector, top_k=10, filters=None, collection="default", **kwargs):
        # Simple mock - return all records
        results = []
        for (rid, coll), r in self._data.items():
            if coll == collection:
                results.append({"id": rid, "score": 0.5, "metadata": r.get("metadata", {})})
        return results[:top_k]

    def get_by_ids(self, ids, collection="default", **kwargs):
        results = []
        for rid in ids:
            key = (rid, collection)
            if key in self._data:
                results.append({"id": rid, "metadata": self._data[key].get("metadata", {})})
        return results

    def delete_by_metadata(self, filter, collection="default", **kwargs):
        to_delete = []
        for (rid, coll), r in self._data.items():
            if coll == collection:
                meta = r.get("metadata", {})
                if all(meta.get(k) == v for k, v in filter.items()):
                    to_delete.append((rid, coll))
        for key in to_delete:
            del self._data[key]


class TestVectorStoreFactory:
    """Test VectorStoreFactory.create method."""

    def test_create_chroma_store(self):
        """Test creating a Chroma VectorStore."""
        settings = Settings()
        settings.vector_store.backend = "chroma"
        settings.vector_store.persist_path = "./data/db/chroma"

        store = VectorStoreFactory.create(settings)
        assert isinstance(store, ChromaStore)
        assert store.persist_path == "./data/db/chroma"

    def test_create_unsupported_provider_raises_error(self):
        """Test that unsupported provider raises ValueError."""
        settings = Settings()
        settings.vector_store.backend = "unsupported"
        settings.vector_store.persist_path = "./data/db/store"

        with pytest.raises(ValueError) as exc_info:
            VectorStoreFactory.create(settings)
        assert "Unsupported VectorStore provider" in str(exc_info.value)

    def test_register_provider(self):
        """Test registering a new provider."""
        VectorStoreFactory.register_provider("fake", FakeVectorStore)

        settings = Settings()
        settings.vector_store.backend = "fake"
        settings.vector_store.persist_path = "./data/db/store"

        store = VectorStoreFactory.create(settings)
        assert isinstance(store, FakeVectorStore)


class TestBaseVectorStoreContract:
    """Contract tests ensuring BaseVectorStore interface is implemented."""

    def test_chroma_store_has_upsert(self):
        """Test ChromaStore has upsert method."""
        store = ChromaStore(persist_path="./data/db/chroma")
        assert hasattr(store, "upsert")
        assert callable(store.upsert)

    def test_chroma_store_has_query(self):
        """Test ChromaStore has query method."""
        store = ChromaStore(persist_path="./data/db/chroma")
        assert hasattr(store, "query")
        assert callable(store.query)

    def test_chroma_store_has_get_by_ids(self):
        """Test ChromaStore has get_by_ids method."""
        store = ChromaStore(persist_path="./data/db/chroma")
        assert hasattr(store, "get_by_ids")
        assert callable(store.get_by_ids)

    def test_chroma_store_has_delete_by_metadata(self):
        """Test ChromaStore has delete_by_metadata method."""
        store = ChromaStore(persist_path="./data/db/chroma")
        assert hasattr(store, "delete_by_metadata")
        assert callable(store.delete_by_metadata)

    def test_fake_store_upsert_and_query(self):
        """Test that FakeVectorStore can upsert and query."""
        store = FakeVectorStore()

        # Upsert a record
        records = [
            {
                "id": "doc1",
                "embedding": [0.1, 0.2, 0.3],
                "metadata": {"source": "test"},
                "text": "Test document",
            }
        ]
        store.upsert(records, collection="test")

        # Query
        results = store.query([0.1, 0.2, 0.3], collection="test")
        assert len(results) == 1
        assert results[0]["id"] == "doc1"

    def test_fake_store_get_by_ids(self):
        """Test FakeVectorStore get_by_ids."""
        store = FakeVectorStore()

        records = [
            {
                "id": "doc1",
                "embedding": [0.1, 0.2, 0.3],
                "metadata": {"source": "test"},
            }
        ]
        store.upsert(records)

        results = store.get_by_ids(["doc1"])
        assert len(results) == 1
        assert results[0]["id"] == "doc1"

    def test_fake_store_delete_by_metadata(self):
        """Test FakeVectorStore delete_by_metadata."""
        store = FakeVectorStore()

        records = [
            {
                "id": "doc1",
                "embedding": [0.1, 0.2, 0.3],
                "metadata": {"source": "test", "category": "a"},
            },
            {
                "id": "doc2",
                "embedding": [0.4, 0.5, 0.6],
                "metadata": {"source": "test", "category": "b"},
            },
        ]
        store.upsert(records)

        # Delete by metadata
        store.delete_by_metadata({"category": "a"})

        # Verify only doc2 remains
        results = store.get_by_ids(["doc1", "doc2"])
        assert len(results) == 1
        assert results[0]["id"] == "doc2"
