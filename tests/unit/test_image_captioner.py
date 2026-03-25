"""Tests for image captioner."""

from src.core.types import Chunk
from src.ingestion.transform.image_captioner import ImageCaptioner


class TestImageCaptioner:
    """Test ImageCaptioner functionality."""

    def test_extract_image_refs_markdown(self):
        """Test extraction of markdown image references."""
        captioner = ImageCaptioner(vision_llm=None)
        text = "这是一段文字 ![alt text](path/to/image.png) 这里是更多文字"
        refs = captioner._extract_image_refs(text)
        assert "path/to/image.png" in refs

    def test_extract_image_refs_multiple(self):
        """Test extraction of multiple image references."""
        captioner = ImageCaptioner(vision_llm=None)
        text = "![img1](path1.png) and ![img2](path2.jpg)"
        refs = captioner._extract_image_refs(text)
        assert "path1.png" in refs
        assert "path2.jpg" in refs

    def test_extract_image_refs_custom_syntax(self):
        """Test extraction of custom [image:path] syntax."""
        captioner = ImageCaptioner(vision_llm=None)
        text = "这是一个医学图像 [image:./images/lab_report.png]"
        refs = captioner._extract_image_refs(text)
        assert "./images/lab_report.png" in refs

    def test_extract_image_refs_none(self):
        """Test extraction when no images present."""
        captioner = ImageCaptioner(vision_llm=None)
        text = "这是一段没有图片的文字。"
        refs = captioner._extract_image_refs(text)
        assert refs == []

    def test_transform_without_vision_llm(self):
        """Test transform without Vision LLM marks for manual processing."""
        captioner = ImageCaptioner(vision_llm=None)
        chunks = [
            Chunk(
                chunk_id="c1",
                text="这是一段文字 ![img](path.png)",
                source_ref="doc1",
                chunk_index=0,
            ),
        ]

        result = captioner.transform(chunks)

        assert len(result) == 1
        assert result[0].metadata["has_unprocessed_images"] is True
        assert "path.png" in result[0].metadata["image_refs"]

    def test_transform_without_images(self):
        """Test transform on chunks without images."""
        captioner = ImageCaptioner(vision_llm=None)
        chunks = [
            Chunk(
                chunk_id="c1",
                text="这是一段没有图片的文字。",
                source_ref="doc1",
                chunk_index=0,
            ),
        ]

        result = captioner.transform(chunks)

        assert len(result) == 1
        assert "has_unprocessed_images" not in result[0].metadata

    def test_transform_preserves_chunk_id(self):
        """Test that chunk IDs are preserved."""
        captioner = ImageCaptioner(vision_llm=None)
        chunks = [
            Chunk(chunk_id="test_id", text="![img](path.png)", source_ref="doc1", chunk_index=0),
        ]

        result = captioner.transform(chunks)

        assert result[0].chunk_id == "test_id"

    def test_transform_preserves_original_metadata(self):
        """Test that original metadata is preserved."""
        captioner = ImageCaptioner(vision_llm=None)
        chunks = [
            Chunk(
                chunk_id="c1",
                text="![img](path.png)",
                metadata={"custom": "value"},
                source_ref="doc1",
                chunk_index=0,
            ),
        ]

        result = captioner.transform(chunks)

        assert result[0].metadata["custom"] == "value"
