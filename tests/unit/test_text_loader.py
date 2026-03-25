"""Tests for text loader."""

import tempfile

import pytest

from src.core.types import Document
from src.libs.loader.text_loader import TextLoader


class TestTextLoader:
    """Test TextLoader functionality."""

    def test_load_txt_file(self):
        """Test loading a .txt file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = f"{tmpdir}/test.txt"
            content = "This is a test document.\nWith multiple lines."
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            loader = TextLoader()
            doc = loader.load(file_path)

            assert isinstance(doc, Document)
            assert doc.text == content
            assert doc.doc_id is not None
            assert len(doc.doc_id) == 16
            assert doc.metadata["file_name"] == "test.txt"
            assert doc.metadata["file_extension"] == ".txt"

    def test_load_md_file(self):
        """Test loading a .md file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = f"{tmpdir}/test.md"
            content = """# Document Title

This is a markdown document.
"""
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            loader = TextLoader()
            doc = loader.load(file_path)

            assert isinstance(doc, Document)
            assert "# Document Title" in doc.text
            assert doc.metadata["title"] == "Document Title"

    def test_load_file_not_found(self):
        """Test loading a non-existent file raises FileNotFoundError."""
        loader = TextLoader()
        with pytest.raises(FileNotFoundError):
            loader.load("/nonexistent/file.txt")

    def test_load_unsupported_extension(self):
        """Test loading unsupported file raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = f"{tmpdir}/test.pdf"
            with open(file_path, "w") as f:
                f.write("content")

            loader = TextLoader()
            with pytest.raises(ValueError) as exc_info:
                loader.load(file_path)
            assert "Unsupported file extension" in str(exc_info.value)

    def test_doc_id_consistency(self):
        """Test that same content produces same doc_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = f"{tmpdir}/file1.txt"
            file2 = f"{tmpdir}/file2.txt"
            content = "Same content"

            with open(file1, "w") as f:
                f.write(content)
            with open(file2, "w") as f:
                f.write(content)

            loader = TextLoader()
            doc1 = loader.load(file1)
            doc2 = loader.load(file2)

            assert doc1.doc_id == doc2.doc_id

    def test_metadata_includes_path(self):
        """Test that metadata includes full path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = f"{tmpdir}/test.txt"
            with open(file_path, "w") as f:
                f.write("content")

            loader = TextLoader()
            doc = loader.load(file_path)

            assert "file_path" in doc.metadata
            assert doc.metadata["file_path"].endswith("test.txt")
            assert "file_size" in doc.metadata
            assert doc.metadata["file_size"] > 0
