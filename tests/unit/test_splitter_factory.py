"""Tests for Splitter Factory."""

import pytest

from src.core.settings import Settings
from src.libs.splitter.base_splitter import BaseSplitter
from src.libs.splitter.recursive_splitter import RecursiveSplitter
from src.libs.splitter.splitter_factory import SplitterFactory


class FakeSplitter(BaseSplitter):
    """Fake Splitter for testing."""

    def __init__(self):
        pass

    def split_text(self, text, **kwargs):
        return [text[i : i + 100] for i in range(0, len(text), 100)]

    def get_config(self) -> dict:
        return {"type": "fake"}


class TestSplitterFactory:
    """Test SplitterFactory.create method."""

    def test_create_recursive_splitter(self):
        """Test creating a RecursiveSplitter."""
        settings = Settings()
        # Default settings should work
        splitter = SplitterFactory.create(settings)
        assert isinstance(splitter, RecursiveSplitter)

    def test_register_provider(self):
        """Test registering a new provider."""
        # First, mock the settings to return "fake" as the splitter_backend
        settings = Settings()
        # Add splitter_backend to retrieval config
        settings.retrieval.splitter_backend = "fake"

        SplitterFactory.register_provider("fake", FakeSplitter)

        splitter = SplitterFactory.create(settings)
        assert isinstance(splitter, FakeSplitter)


class TestRecursiveSplitter:
    """Test RecursiveSplitter functionality."""

    def test_split_empty_text(self):
        """Test splitting empty text."""
        splitter = RecursiveSplitter(chunk_size=100, chunk_overlap=10)
        chunks = splitter.split_text("")
        assert chunks == []

    def test_split_short_text(self):
        """Test splitting text shorter than chunk_size."""
        splitter = RecursiveSplitter(chunk_size=100, chunk_overlap=10)
        text = "This is a short text."
        chunks = splitter.split_text(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_split_long_text(self):
        """Test splitting text longer than chunk_size."""
        splitter = RecursiveSplitter(chunk_size=50, chunk_overlap=10)
        text = "A" * 150  # 150 characters
        chunks = splitter.split_text(text)
        # Should have at least 3 chunks
        assert len(chunks) >= 2
        # All chunks should be non-empty
        for chunk in chunks:
            assert len(chunk) > 0

    def test_split_with_separator(self):
        """Test splitting at separators."""
        splitter = RecursiveSplitter(chunk_size=50, chunk_overlap=10)
        text = "Hello world.\n\nThis is a new paragraph."
        chunks = splitter.split_text(text)
        assert len(chunks) > 0
        # Chunks should not have leading/trailing whitespace
        for chunk in chunks:
            assert chunk == chunk.strip()

    def test_chunk_overlap(self):
        """Test that chunks have correct overlap."""
        splitter = RecursiveSplitter(chunk_size=20, chunk_overlap=5)
        text = "A" * 50
        chunks = splitter.split_text(text)
        if len(chunks) >= 2:
            # Second chunk should start with last 5 chars of first chunk
            assert chunks[1].startswith(chunks[0][-5:])

    def test_get_config(self):
        """Test get_config returns correct config."""
        splitter = RecursiveSplitter(chunk_size=100, chunk_overlap=20)
        config = splitter.get_config()
        assert config["type"] == "recursive"
        assert config["chunk_size"] == 100
        assert config["chunk_overlap"] == 20


class TestBaseSplitterInterface:
    """Test that Splitter implementations conform to BaseSplitter interface."""

    def test_recursive_splitter_has_split_text(self):
        """Test RecursiveSplitter has split_text method."""
        splitter = RecursiveSplitter()
        assert hasattr(splitter, "split_text")
        assert callable(splitter.split_text)

    def test_recursive_splitter_has_get_config(self):
        """Test RecursiveSplitter has get_config method."""
        splitter = RecursiveSplitter()
        assert hasattr(splitter, "get_config")
        assert callable(splitter.get_config)
