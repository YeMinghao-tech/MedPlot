"""Tests for chunk refiner."""

from src.core.types import Chunk
from src.ingestion.transform.chunk_refiner import ChunkRefiner


class TestChunkRefiner:
    """Test ChunkRefiner functionality."""

    def test_rule_based_refine_removes_excessive_whitespace(self):
        """Test that excessive whitespace is removed."""
        refiner = ChunkRefiner(llm=None)
        text = "这是    一些    文本"
        result = refiner._rule_based_refine(text)
        assert "    " not in result
        assert result == "这是 一些 文本"

    def test_rule_based_refine_normalizes_punctuation(self):
        """Test that repeated punctuation is normalized."""
        refiner = ChunkRefiner(llm=None)
        text = "这是文本。。。还有更多！！！"
        result = refiner._rule_based_refine(text)
        assert "。。" not in result
        assert "！！" not in result

    def test_rule_based_refine_removes_line_whitespace(self):
        """Test that leading/trailing whitespace per line is removed."""
        refiner = ChunkRefiner(llm=None)
        text = "  第一行\n  第二行  \n  第三行  "
        result = refiner._rule_based_refine(text)
        assert not result.startswith(" ")
        assert "第一行" in result
        assert "第二行" in result

    def test_transform_without_llm(self):
        """Test transform with rule-based refinement only."""
        refiner = ChunkRefiner(llm=None)
        chunks = [
            Chunk(chunk_id="c1", text="文本1    ", source_ref="doc1", chunk_index=0),
            Chunk(chunk_id="c2", text="文本2", source_ref="doc1", chunk_index=1),
        ]

        result = refiner.transform(chunks)

        assert len(result) == 2
        assert result[0].metadata["refined"] is True
        assert result[0].metadata["llm_enhanced"] is False

    def test_transform_preserves_chunk_id(self):
        """Test that chunk IDs are preserved through transformation."""
        refiner = ChunkRefiner(llm=None)
        chunks = [
            Chunk(chunk_id="test_id", text="文本", source_ref="doc1", chunk_index=0),
        ]

        result = refiner.transform(chunks)

        assert result[0].chunk_id == "test_id"

    def test_transform_preserves_metadata(self):
        """Test that original metadata is preserved."""
        refiner = ChunkRefiner(llm=None)
        chunks = [
            Chunk(
                chunk_id="c1",
                text="文本",
                metadata={"custom": "value", "parent": "doc1"},
                source_ref="doc1",
                chunk_index=0,
            ),
        ]

        result = refiner.transform(chunks)

        assert result[0].metadata["custom"] == "value"
        assert result[0].metadata["parent"] == "doc1"

    def test_llm_refine_fallback(self):
        """Test that LLM failure falls back to rule-based."""
        # Create a mock LLM that raises exception
        class FailingLLM:
            def chat(self, messages):
                raise Exception("LLM error")

        refiner = ChunkRefiner(llm=FailingLLM())
        chunks = [
            Chunk(chunk_id="c1", text="文本", source_ref="doc1", chunk_index=0),
        ]

        # Should not raise, should fall back
        result = refiner.transform(chunks)

        assert len(result) == 1
        assert result[0].metadata["llm_enhanced"] is True  # LLM was attempted

    def test_transform_empty_text(self):
        """Test transforming chunk with empty text."""
        refiner = ChunkRefiner(llm=None)
        chunks = [
            Chunk(chunk_id="c1", text="", source_ref="doc1", chunk_index=0),
        ]

        result = refiner.transform(chunks)

        assert len(result) == 1
        assert result[0].text == ""
