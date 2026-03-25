"""Tests for ingestion pipeline."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.types import Chunk, Document
from src.ingestion.pipeline import IngestionPipeline, IngestionResult


class FakeVectorStore:
    """Fake vector store for testing."""

    def __init__(self):
        self.upserted = []

    def upsert(self, records, collection="default"):
        self.upserted.extend(records)


class FakeEmbedding:
    """Fake embedding for testing."""

    def embed(self, texts, **kwargs):
        return [[0.1, 0.2, 0.3] for _ in texts]


class TestIngestionPipeline:
    """Test IngestionPipeline functionality."""

    def test_run_with_no_files(self):
        """Test running pipeline on empty directory."""
        fake_store = FakeVectorStore()
        settings = MagicMock()

        pipeline = IngestionPipeline(
            settings=settings,
            vector_store=fake_store,
            embedding_client=FakeEmbedding(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            result = pipeline.run(tmpdir)

        assert result.total_files == 0
        assert result.processed_files == 0
        assert result.skipped_files == 0
        assert result.failed_files == 0
        assert result.total_chunks == 0

    def test_run_with_txt_file(self):
        """Test running pipeline on a single txt file."""
        fake_store = FakeVectorStore()
        settings = MagicMock()

        pipeline = IngestionPipeline(
            settings=settings,
            vector_store=fake_store,
            embedding_client=FakeEmbedding(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("This is a test document.")

            result = pipeline.run(tmpdir)

        assert result.total_files == 1
        assert result.processed_files == 1
        assert result.skipped_files == 0
        assert result.failed_files == 0
        assert result.total_chunks >= 1

    def test_run_with_md_file(self):
        """Test running pipeline on a markdown file."""
        fake_store = FakeVectorStore()
        settings = MagicMock()

        pipeline = IngestionPipeline(
            settings=settings,
            vector_store=fake_store,
            embedding_client=FakeEmbedding(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.md"
            test_file.write_text("# Header\n\nSome content here.")

            result = pipeline.run(tmpdir)

        assert result.total_files == 1
        assert result.processed_files == 1

    def test_run_with_nested_files(self):
        """Test running pipeline on nested directories."""
        fake_store = FakeVectorStore()
        settings = MagicMock()

        pipeline = IngestionPipeline(
            settings=settings,
            vector_store=fake_store,
            embedding_client=FakeEmbedding(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            (subdir / "doc1.txt").write_text("Content 1")
            (subdir / "doc2.md").write_text("Content 2")

            result = pipeline.run(tmpdir)

        assert result.total_files == 2
        assert result.processed_files == 2

    def test_run_with_force_reload(self):
        """Test force reload ignores integrity check."""
        fake_store = FakeVectorStore()
        settings = MagicMock()

        pipeline = IngestionPipeline(
            settings=settings,
            vector_store=fake_store,
            embedding_client=FakeEmbedding(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Test content")

            # First run
            result1 = pipeline.run(tmpdir, force=False)
            # Second run without force should skip
            result2 = pipeline.run(tmpdir, force=False)

            assert result1.processed_files == 1
            assert result2.skipped_files == 1

            # Force reload
            result3 = pipeline.run(tmpdir, force=True)
            assert result3.processed_files == 1

    def test_run_progress_callback(self):
        """Test progress callback is called."""
        fake_store = FakeVectorStore()
        settings = MagicMock()

        progress_calls = []

        def on_progress(stage, current, total):
            progress_calls.append((stage, current, total))

        pipeline = IngestionPipeline(
            settings=settings,
            vector_store=fake_store,
            embedding_client=FakeEmbedding(),
            on_progress=on_progress,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Test content")

            pipeline.run(tmpdir)

        assert len(progress_calls) > 0
        stages = [c[0] for c in progress_calls]
        assert "load" in stages

    def test_run_collection_parameter(self):
        """Test collection parameter is passed to upsert."""
        fake_store = FakeVectorStore()
        settings = MagicMock()

        pipeline = IngestionPipeline(
            settings=settings,
            vector_store=fake_store,
            embedding_client=FakeEmbedding(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Test content for collection")

            pipeline.run(tmpdir, collection="my_collection")

        # Vector store upsert was called with collection
        assert len(fake_store.upserted) > 0

    def test_ingestion_result_defaults(self):
        """Test IngestionResult default values."""
        result = IngestionResult()

        assert result.total_files == 0
        assert result.processed_files == 0
        assert result.skipped_files == 0
        assert result.failed_files == 0
        assert result.total_chunks == 0
        assert result.duration_seconds == 0.0
        assert result.errors == []

    def test_ingestion_result_with_errors(self):
        """Test IngestionResult tracks errors."""
        result = IngestionResult()
        result.failed_files = 1
        result.errors.append("test.txt: Some error")

        assert len(result.errors) == 1
        assert "test.txt" in result.errors[0]
