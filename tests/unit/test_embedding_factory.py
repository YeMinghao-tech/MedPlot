"""Tests for Embedding Factory."""

import pytest

from src.core.settings import Settings
from src.libs.embedding.base_embedding import BaseEmbedding
from src.libs.embedding.dashscope_embedding import DashScopeEmbedding
from src.libs.embedding.embedding_factory import EmbeddingFactory
from src.libs.embedding.ollama_embedding import OllamaEmbedding
from src.libs.embedding.openai_embedding import OpenAIEmbedding


class FakeEmbedding(BaseEmbedding):
    """Fake Embedding for testing."""

    def __init__(self, model: str = "fake-embedding"):
        self.model = model
        self._dimension = 384

    def embed(self, texts, **kwargs):
        return [[0.1] * self._dimension for _ in texts]

    def get_model_name(self) -> str:
        return self.model

    def get_dimension(self) -> int:
        return self._dimension


class TestEmbeddingFactory:
    """Test EmbeddingFactory.create method."""

    def test_create_dashscope_embedding(self):
        """Test creating a DashScope Embedding."""
        settings = Settings()
        settings.embedding.provider = "dashscope"
        settings.embedding.model = "text-embedding-v1"

        embed = EmbeddingFactory.create(settings)
        assert isinstance(embed, DashScopeEmbedding)
        assert embed.model == "text-embedding-v1"

    def test_create_openai_embedding(self):
        """Test creating an OpenAI Embedding."""
        settings = Settings()
        settings.embedding.provider = "openai"
        settings.embedding.model = "text-embedding-ada-002"

        embed = EmbeddingFactory.create(settings)
        assert isinstance(embed, OpenAIEmbedding)
        assert embed.model == "text-embedding-ada-002"

    def test_create_ollama_embedding(self):
        """Test creating an Ollama Embedding."""
        settings = Settings()
        settings.embedding.provider = "ollama"
        settings.embedding.model = "nomic-embed-text"

        embed = EmbeddingFactory.create(settings)
        assert isinstance(embed, OllamaEmbedding)
        assert embed.model == "nomic-embed-text"

    def test_create_unsupported_provider_raises_error(self):
        """Test that unsupported provider raises ValueError."""
        settings = Settings()
        settings.embedding.provider = "unsupported"
        settings.embedding.model = "some-model"

        with pytest.raises(ValueError) as exc_info:
            EmbeddingFactory.create(settings)
        assert "Unsupported Embedding provider" in str(exc_info.value)

    def test_provider_case_insensitive(self):
        """Test that provider names are case-insensitive."""
        settings = Settings()
        settings.embedding.provider = "DASHSCOPE"
        settings.embedding.model = "text-embedding-v1"

        embed = EmbeddingFactory.create(settings)
        assert isinstance(embed, DashScopeEmbedding)

    def test_register_provider(self):
        """Test registering a new provider."""
        EmbeddingFactory.register_provider("fake", FakeEmbedding)

        settings = Settings()
        settings.embedding.provider = "fake"
        settings.embedding.model = "fake-model"

        embed = EmbeddingFactory.create(settings)
        assert isinstance(embed, FakeEmbedding)


class TestBaseEmbeddingInterface:
    """Test that Embedding implementations conform to BaseEmbedding interface."""

    def test_dashscope_embedding_has_embed_method(self):
        """Test DashScopeEmbedding has embed method."""
        embed = DashScopeEmbedding()
        assert hasattr(embed, "embed")
        assert callable(embed.embed)

    def test_dashscope_embedding_has_get_model_name(self):
        """Test DashScopeEmbedding has get_model_name method."""
        embed = DashScopeEmbedding()
        assert hasattr(embed, "get_model_name")
        assert callable(embed.get_model_name)

    def test_dashscope_embedding_has_get_dimension(self):
        """Test DashScopeEmbedding has get_dimension method."""
        embed = DashScopeEmbedding()
        assert hasattr(embed, "get_dimension")
        assert callable(embed.get_dimension)
        assert embed.get_dimension() == 1536
