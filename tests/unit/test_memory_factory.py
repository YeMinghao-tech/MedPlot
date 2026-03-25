"""Tests for Memory Factory."""

import tempfile

import pytest

from src.core.settings import Settings
from src.libs.memory.base_memory import (
    BaseEpisodicMemory,
    BaseSemanticMemory,
    BaseWorkingMemory,
)
from src.libs.memory.chroma_memory import ChromaEpisodicMemory
from src.libs.memory.in_memory_working import InMemoryWorkingMemory
from src.libs.memory.memory_factory import MemoryFactory
from src.libs.memory.sqlite_memory import SQLiteSemanticMemory


class TestMemoryFactory:
    """Test MemoryFactory methods."""

    def test_create_working_memory_in_memory(self):
        """Test creating in-memory working memory."""
        settings = Settings()
        settings.memory.working.backend = "in_memory"

        memory = MemoryFactory.create_working(settings)
        assert isinstance(memory, InMemoryWorkingMemory)
        assert isinstance(memory, BaseWorkingMemory)

    def test_create_working_memory_unsupported(self):
        """Test that unsupported working memory raises error."""
        settings = Settings()
        settings.memory.working.backend = "unsupported"

        with pytest.raises(ValueError) as exc_info:
            MemoryFactory.create_working(settings)
        assert "Unsupported working memory backend" in str(exc_info.value)

    def test_create_semantic_memory_sqlite(self):
        """Test creating SQLite semantic memory."""
        settings = Settings()
        settings.memory.semantic.backend = "sqlite"
        settings.memory.semantic.db_path = "./data/test_profiles.db"

        memory = MemoryFactory.create_semantic(settings)
        assert isinstance(memory, SQLiteSemanticMemory)
        assert isinstance(memory, BaseSemanticMemory)

    def test_create_semantic_memory_unsupported(self):
        """Test that unsupported semantic memory raises error."""
        settings = Settings()
        settings.memory.semantic.backend = "unsupported"
        settings.memory.semantic.db_path = "./data/test.db"

        with pytest.raises(ValueError) as exc_info:
            MemoryFactory.create_semantic(settings)
        assert "Unsupported semantic memory backend" in str(exc_info.value)

    def test_create_episodic_memory_chroma(self):
        """Test creating Chroma episodic memory."""
        settings = Settings()
        settings.memory.episodic.backend = "chroma"
        settings.memory.episodic.collection = "test_episodes"
        settings.memory.episodic.metadata_db = "./data/test_metadata.db"

        memory = MemoryFactory.create_episodic(settings)
        assert isinstance(memory, ChromaEpisodicMemory)
        assert isinstance(memory, BaseEpisodicMemory)


class TestInMemoryWorkingMemory:
    """Test InMemoryWorkingMemory functionality."""

    def test_set_and_get(self):
        """Test setting and getting memory."""
        memory = InMemoryWorkingMemory()
        state = {"symptoms": ["fever"], "department": "internal"}
        memory.set("session1", state)
        result = memory.get("session1")
        assert result == state

    def test_get_nonexistent(self):
        """Test getting nonexistent session returns None."""
        memory = InMemoryWorkingMemory()
        result = memory.get("nonexistent")
        assert result is None

    def test_delete(self):
        """Test deleting memory."""
        memory = InMemoryWorkingMemory()
        memory.set("session1", {"test": "data"})
        memory.delete("session1")
        result = memory.get("session1")
        assert result is None

    def test_clear(self):
        """Test clearing all memory."""
        memory = InMemoryWorkingMemory()
        memory.set("session1", {"test": "data1"})
        memory.set("session2", {"test": "data2"})
        memory.clear()
        assert memory.get("session1") is None
        assert memory.get("session2") is None


class TestSQLiteSemanticMemory:
    """Test SQLiteSemanticMemory functionality."""

    def test_upsert_and_get(self):
        """Test upserting and getting patient profile."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            memory = SQLiteSemanticMemory(db_path=db_path)
            profile = {"name": "张三", "age": 45, "allergies": ["青霉素"]}
            memory.upsert("patient1", profile)

            result = memory.get("patient1")
            assert result is not None
            assert result["name"] == "张三"
            assert result["age"] == 45
        finally:
            import os

            os.unlink(db_path)

    def test_get_nonexistent(self):
        """Test getting nonexistent patient returns None."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            memory = SQLiteSemanticMemory(db_path=db_path)
            result = memory.get("nonexistent")
            assert result is None
        finally:
            import os

            os.unlink(db_path)

    def test_delete(self):
        """Test deleting patient profile."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            memory = SQLiteSemanticMemory(db_path=db_path)
            memory.upsert("patient1", {"name": "测试"})
            memory.delete("patient1")
            result = memory.get("patient1")
            assert result is None
        finally:
            import os

            os.unlink(db_path)


class TestBaseMemoryInterface:
    """Test that Memory implementations conform to base interfaces."""

    def test_in_memory_working_conforms_to_interface(self):
        """Test InMemoryWorkingMemory conforms to BaseWorkingMemory."""
        memory = InMemoryWorkingMemory()
        assert isinstance(memory, BaseWorkingMemory)
        assert hasattr(memory, "get")
        assert hasattr(memory, "set")
        assert hasattr(memory, "delete")

    def test_sqlite_semantic_conforms_to_interface(self):
        """Test SQLiteSemanticMemory conforms to BaseSemanticMemory."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            memory = SQLiteSemanticMemory(db_path=db_path)
            assert isinstance(memory, BaseSemanticMemory)
            assert hasattr(memory, "get")
            assert hasattr(memory, "upsert")
            assert hasattr(memory, "delete")
        finally:
            import os

            os.unlink(db_path)

    def test_chroma_episodic_conforms_to_interface(self):
        """Test ChromaEpisodicMemory conforms to BaseEpisodicMemory."""
        memory = ChromaEpisodicMemory()
        assert isinstance(memory, BaseEpisodicMemory)
        assert hasattr(memory, "add")
        assert hasattr(memory, "search")
        assert hasattr(memory, "get_by_patient")
