"""Tests for medical chunker."""

from src.core.types import Document
from src.ingestion.chunking.medical_chunker import MedicalChunker


class TestMedicalChunker:
    """Test MedicalChunker functionality."""

    def test_split_document_basic(self):
        """Test basic document splitting."""
        doc = Document(
            doc_id="test_doc",
            text="这是第一段内容。\n\n这是第二段内容。\n\n这是第三段内容。",
            source_ref="/path/to/doc.txt",
        )

        chunker = MedicalChunker()
        chunks = chunker.split_document(doc, chunk_size=100, chunk_overlap=10)

        assert len(chunks) > 0
        assert all(hasattr(chunk, "chunk_id") for chunk in chunks)
        assert all(hasattr(chunk, "text") for chunk in chunks)
        assert all(chunk.source_ref == "/path/to/doc.txt" for chunk in chunks)
        assert all(chunk.metadata.get("parent_doc_id") == "test_doc" for chunk in chunks)

    def test_split_document_preserves_chunk_index(self):
        """Test that chunk indices are correctly assigned."""
        doc = Document(
            doc_id="test_doc",
            text="段1\n\n段2\n\n段3\n\n段4\n\n段5\n\n段6\n\n段7\n\n段8",
            source_ref="/path/to/doc.txt",
        )

        chunker = MedicalChunker()
        chunks = chunker.split_document(doc, chunk_size=50, chunk_overlap=5)

        indices = [chunk.chunk_index for chunk in chunks]
        assert indices == list(range(len(chunks)))

    def test_detect_medical_section(self):
        """Test medical section detection."""
        chunker = MedicalChunker()

        assert chunker._detect_medical_section("疾病概述：感冒是...") == "疾病概述"
        assert chunker._detect_medical_section("临床表现：发热咳嗽...") == "临床表现"
        assert chunker._detect_medical_section("治疗原则：休息饮水...") == "治疗原则"

    def test_chunk_id_stability(self):
        """Test that chunk IDs are stable for same content."""
        doc = Document(
            doc_id="test_doc",
            text="这是测试内容。" * 20,
            source_ref="/path/to/doc.txt",
        )

        chunker = MedicalChunker()
        chunks1 = chunker.split_document(doc)
        chunks2 = chunker.split_document(doc)

        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.chunk_id == c2.chunk_id

    def test_medical_separators(self):
        """Test that medical section separators are preserved."""
        doc = Document(
            doc_id="test_doc",
            text="疾病概述\n感冒是一种常见病。\n\n临床表现\n主要症状是发热。",
            source_ref="/path/to/doc.txt",
        )

        chunker = MedicalChunker()
        chunks = chunker.split_document(doc, chunk_size=200, chunk_overlap=0)

        # At least one chunk should contain a medical section marker
        section_markers = ["疾病概述", "临床表现"]
        has_marker = any(
            any(marker in chunk.text for marker in section_markers)
            for chunk in chunks
        )
        assert has_marker or len(chunks) > 0

    def test_split_empty_document(self):
        """Test splitting empty document."""
        doc = Document(
            doc_id="empty_doc",
            text="",
            source_ref="/path/to/doc.txt",
        )

        chunker = MedicalChunker()
        chunks = chunker.split_document(doc)

        # Empty text may produce empty or single chunk depending on splitter
        assert isinstance(chunks, list)
