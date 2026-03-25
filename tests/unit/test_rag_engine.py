"""Tests for RAG Engine components."""

from unittest.mock import MagicMock

from src.tools.rag_engine.hybrid_search import HybridSearch, RetrievalResult
from src.tools.rag_engine.query_processor import QueryProcessor


class TestQueryProcessor:
    """Test QueryProcessor functionality."""

    def test_process_colloquial_terms(self):
        """Test that colloquial terms are mapped to medical terms."""
        processor = QueryProcessor()

        result = processor.process("我发烧了，肚子疼")

        # Should have mapped medical terms
        assert "发烧" in result.medical_terms
        assert result.medical_terms["发烧"] == "发热"
        assert "肚子疼" in result.medical_terms
        assert result.medical_terms["肚子疼"] == "腹痛"

    def test_process_preserves_original(self):
        """Test that original query is preserved."""
        processor = QueryProcessor()

        original = "我头疼"
        result = processor.process(original)

        assert result.original == original

    def test_extract_medical_filters(self):
        """Test filter extraction from query."""
        processor = QueryProcessor()

        result = processor.process("根据指南，心脏病有哪些症状")

        # Should have extracted authority filter
        assert "authority_level" in result.filters

    def test_expand_query(self):
        """Test query expansion."""
        processor = QueryProcessor()

        variants = processor.expand_query("发烧")

        assert len(variants) >= 1
        assert "发烧" in variants

    def test_process_empty_query(self):
        """Test processing empty query."""
        processor = QueryProcessor()

        result = processor.process("")

        assert result.original == ""
        assert len(result.expanded_terms) == 0


class TestHybridSearch:
    """Test HybridSearch functionality."""

    def test_rrf_fusion_combines_results(self):
        """Test that RRF fusion combines dense and sparse results."""
        # Mock vector store
        mock_store = MagicMock()
        mock_store.query.return_value = [
            {"id": "d1", "score": 0.1, "text": "doc1", "metadata": {}},
            {"id": "d2", "score": 0.2, "text": "doc2", "metadata": {}},
        ]
        mock_store.get_by_ids.return_value = [
            {"id": "d1", "text": "doc1", "metadata": {}},
            {"id": "d2", "text": "doc2", "metadata": {}},
        ]

        # Mock embedding
        mock_embedding = MagicMock()
        mock_embedding.embed.return_value = [[0.1, 0.2, 0.3]]

        # Create hybrid search without BM25
        hybrid = HybridSearch(
            vector_store=mock_store,
            embedding_client=mock_embedding,
            bm25_indexer=None,
        )

        results = hybrid.search("test query", top_k=10)

        assert len(results) == 2
        mock_store.query.assert_called_once()

    def test_rrf_fusion_with_both_retrievers(self):
        """Test RRF fusion when both dense and sparse return results."""
        mock_store = MagicMock()
        mock_store.query.return_value = [
            {"id": "d1", "score": 0.1, "text": "doc1", "metadata": {}},
        ]
        mock_store.get_by_ids.return_value = [
            {"id": "d1", "text": "doc1", "metadata": {}},
            {"id": "s1", "text": "sparse1", "metadata": {}},
        ]

        mock_embedding = MagicMock()
        mock_embedding.embed.return_value = [[0.1, 0.2, 0.3]]

        # Mock BM25 indexer
        mock_bm25 = MagicMock()
        mock_bm25.query.return_value = [("s1", 0.5), ("d1", 0.3)]

        hybrid = HybridSearch(
            vector_store=mock_store,
            embedding_client=mock_embedding,
            bm25_indexer=mock_bm25,
        )

        results = hybrid.search("test query", top_k=10)

        assert len(results) >= 1
        mock_bm25.query.assert_called_once()

    def test_search_returns_empty_on_no_results(self):
        """Test that search returns empty list when no results."""
        mock_store = MagicMock()
        mock_store.query.return_value = []
        mock_store.get_by_ids.return_value = []

        mock_embedding = MagicMock()
        mock_embedding.embed.return_value = [[0.1, 0.2, 0.3]]

        hybrid = HybridSearch(
            vector_store=mock_store,
            embedding_client=mock_embedding,
        )

        results = hybrid.search("test query", top_k=10)

        assert results == []

    def test_rrf_k_parameter(self):
        """Test that RRF k parameter affects fusion."""
        mock_store = MagicMock()
        mock_store.query.return_value = [
            {"id": "d1", "score": 0.1, "text": "doc1", "metadata": {}},
        ]
        mock_store.get_by_ids.return_value = [
            {"id": "d1", "text": "doc1", "metadata": {}},
        ]

        mock_embedding = MagicMock()
        mock_embedding.embed.return_value = [[0.1, 0.2, 0.3]]

        hybrid1 = HybridSearch(
            vector_store=mock_store,
            embedding_client=mock_embedding,
            rrf_k=60,
        )

        hybrid2 = HybridSearch(
            vector_store=mock_store,
            embedding_client=mock_embedding,
            rrf_k=10,
        )

        assert hybrid1.rrf_k == 60
        assert hybrid2.rrf_k == 10

    def test_dense_top_k_and_sparse_top_k(self):
        """Test that dense_top_k and sparse_top_k are passed correctly."""
        mock_store = MagicMock()
        mock_store.query.return_value = []
        mock_store.get_by_ids.return_value = []

        mock_embedding = MagicMock()
        mock_embedding.embed.return_value = [[0.1, 0.2, 0.3]]

        hybrid = HybridSearch(
            vector_store=mock_store,
            embedding_client=mock_embedding,
        )

        hybrid.search(
            "query",
            dense_top_k=50,
            sparse_top_k=30,
            collection="test",
        )

        mock_store.query.assert_called_once()
        call_kwargs = mock_store.query.call_args[1]
        assert call_kwargs["top_k"] == 50


class TestRetrievalResult:
    """Test RetrievalResult dataclass."""

    def test_retrieval_result_creation(self):
        """Test creating a RetrievalResult."""
        result = RetrievalResult(
            chunk_id="c1",
            text="test text",
            score=0.95,
            source="dense",
            metadata={"authority_level": 5},
        )

        assert result.chunk_id == "c1"
        assert result.text == "test text"
        assert result.score == 0.95
        assert result.source == "dense"
        assert result.metadata["authority_level"] == 5

    def test_retrieval_result_source_values(self):
        """Test different source values."""
        sources = ["dense", "sparse", "fused", "reranked"]

        for source in sources:
            result = RetrievalResult(
                chunk_id="c1",
                text="text",
                score=0.5,
                source=source,
                metadata={},
            )
            assert result.source == source
