"""Tests for Reranker Factory."""

import pytest

from src.core.settings import Settings
from src.libs.reranker.base_reranker import BaseReranker
from src.libs.reranker.bge_reranker import BGEReranker
from src.libs.reranker.llm_reranker import LLMReranker
from src.libs.reranker.none_reranker import NoneReranker
from src.libs.reranker.reranker_factory import RerankerFactory


class FakeReranker(BaseReranker):
    """Fake Reranker for testing."""

    def __init__(self):
        self.model = "fake-reranker"

    def rerank(self, query, candidates, **kwargs):
        return candidates

    def get_model_name(self) -> str:
        return self.model


class TestRerankerFactory:
    """Test RerankerFactory.create method."""

    def test_create_bge_reranker(self):
        """Test creating a BGE Reranker."""
        settings = Settings()
        settings.retrieval.rerank_backend = "bge"
        settings.retrieval.rerank_model = "BAAI/bge-reranker-v2-m3"

        reranker = RerankerFactory.create(settings)
        assert isinstance(reranker, BGEReranker)
        assert reranker.model == "BAAI/bge-reranker-v2-m3"

    def test_create_none_reranker(self):
        """Test creating a None Reranker."""
        settings = Settings()
        settings.retrieval.rerank_backend = "none"
        settings.retrieval.rerank_model = "BAAI/bge-reranker-v2-m3"

        reranker = RerankerFactory.create(settings)
        assert isinstance(reranker, NoneReranker)

    def test_create_unsupported_provider_raises_error(self):
        """Test that unsupported provider raises ValueError."""
        settings = Settings()
        settings.retrieval.rerank_backend = "unsupported"
        settings.retrieval.rerank_model = "some-model"

        with pytest.raises(ValueError) as exc_info:
            RerankerFactory.create(settings)
        assert "Unsupported Reranker provider" in str(exc_info.value)

    def test_register_provider(self):
        """Test registering a new provider."""
        settings = Settings()
        settings.retrieval.rerank_backend = "fake"
        settings.retrieval.rerank_model = "some-model"

        RerankerFactory.register_provider("fake", FakeReranker)

        reranker = RerankerFactory.create(settings)
        assert isinstance(reranker, FakeReranker)


class TestNoneReranker:
    """Test NoneReranker functionality."""

    def test_rerank_returns_same_order(self):
        """Test that NoneReranker returns candidates unchanged."""
        reranker = NoneReranker()
        candidates = [
            {"id": "1", "text": "doc1", "score": 0.9},
            {"id": "2", "text": "doc2", "score": 0.8},
            {"id": "3", "text": "doc3", "score": 0.7},
        ]
        result = reranker.rerank("query", candidates)
        assert result == candidates

    def test_rerank_respects_top_k(self):
        """Test that NoneReranker respects top_k parameter."""
        reranker = NoneReranker()
        candidates = [
            {"id": str(i), "text": f"doc{i}", "score": 1.0 - i * 0.1}
            for i in range(10)
        ]
        result = reranker.rerank("query", candidates, top_k=3)
        assert len(result) == 3
        assert result == candidates[:3]

    def test_rerank_empty_candidates(self):
        """Test that NoneReranker handles empty candidates."""
        reranker = NoneReranker()
        result = reranker.rerank("query", [])
        assert result == []

    def test_get_model_name(self):
        """Test NoneReranker model name."""
        reranker = NoneReranker()
        assert reranker.get_model_name() == "none"


class TestBaseRerankerInterface:
    """Test that Reranker implementations conform to BaseReranker interface."""

    def test_bge_reranker_has_rerank(self):
        """Test BGEReranker has rerank method."""
        reranker = BGEReranker()
        assert hasattr(reranker, "rerank")
        assert callable(reranker.rerank)

    def test_bge_reranker_has_get_model_name(self):
        """Test BGEReranker has get_model_name method."""
        reranker = BGEReranker()
        assert hasattr(reranker, "get_model_name")
        assert callable(reranker.get_model_name)
        assert reranker.get_model_name() == "BAAI/bge-reranker-v2-m3"

    def test_none_reranker_has_rerank(self):
        """Test NoneReranker has rerank method."""
        reranker = NoneReranker()
        assert hasattr(reranker, "rerank")
        assert callable(reranker.rerank)
