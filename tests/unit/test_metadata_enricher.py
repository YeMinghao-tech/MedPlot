"""Tests for metadata enricher."""

from src.core.types import Chunk
from src.ingestion.transform.metadata_enricher import MetadataEnricher


class TestMetadataEnricher:
    """Test MetadataEnricher functionality."""

    def test_extract_disease_tags(self):
        """Test disease tag extraction."""
        enricher = MetadataEnricher()
        text = "感冒是一种常见疾病，主要表现为发热、咳嗽等症状。"
        tags = enricher._extract_disease_tags(text)
        assert "感冒" in tags
        assert "发热" in tags
        assert "咳嗽" in tags

    def test_extract_disease_tags_limits(self):
        """Test that disease tags are limited."""
        enricher = MetadataEnricher()
        # Create text with many disease mentions
        text = "感冒发烧咳嗽哮喘肺炎胃炎肠炎肝炎心肌炎脑炎肾炎关节炎白血病糖尿病高血压心脏病"
        tags = enricher._extract_disease_tags(text)
        assert len(tags) <= 10

    def test_calculate_authority_level_from_metadata(self):
        """Test authority level from metadata takes precedence."""
        enricher = MetadataEnricher()
        metadata = {"authority_level": 5}
        level = enricher._calculate_authority_level("some text", metadata)
        assert level == 5

    def test_calculate_authority_level_from_content(self):
        """Test authority level calculated from content."""
        enricher = MetadataEnricher()

        # Level 5: guidelines
        text = "根据国家卫健委指南和WHO标准"
        level = enricher._calculate_authority_level(text, {})
        assert level == 5

        # Level 4: expert opinion
        text = "专家共识认为"
        level = enricher._calculate_authority_level(text, {})
        assert level >= 4  # "专家" matches level 4 or higher

        # Level 1: general text
        text = "一般来说，建议多喝水。"
        level = enricher._calculate_authority_level(text, {})
        assert level >= 1

    def test_extract_medical_keywords(self):
        """Test medical keyword extraction."""
        enricher = MetadataEnricher()
        text = "患者需要进行检查，包括CT和MRI检查，然后进行药物治疗。"
        keywords = enricher._extract_medical_keywords(text)
        assert "检查" in keywords
        assert "CT" in keywords
        assert "MRI" in keywords
        assert "药物" in keywords

    def test_transform_adds_metadata(self):
        """Test that transform adds enrichment metadata."""
        enricher = MetadataEnricher()
        chunks = [
            Chunk(
                chunk_id="c1",
                text="感冒的症状包括发热和咳嗽。",
                source_ref="doc1",
                chunk_index=0,
            ),
        ]

        result = enricher.transform(chunks)

        assert len(result) == 1
        assert result[0].metadata["enriched"] is True
        assert "disease_tags" in result[0].metadata
        assert "authority_level" in result[0].metadata
        assert "medical_keywords" in result[0].metadata

    def test_transform_preserves_original_metadata(self):
        """Test that original metadata is preserved."""
        enricher = MetadataEnricher()
        chunks = [
            Chunk(
                chunk_id="c1",
                text="感冒的症状",
                metadata={"custom": "value", "parent_doc_id": "doc1"},
                source_ref="doc1",
                chunk_index=0,
            ),
        ]

        result = enricher.transform(chunks)

        assert result[0].metadata["custom"] == "value"
        assert result[0].metadata["parent_doc_id"] == "doc1"

    def test_transform_preserves_chunk_id(self):
        """Test that chunk IDs are preserved."""
        enricher = MetadataEnricher()
        chunks = [
            Chunk(chunk_id="test_id", text="文本", source_ref="doc1", chunk_index=0),
        ]

        result = enricher.transform(chunks)

        assert result[0].chunk_id == "test_id"
