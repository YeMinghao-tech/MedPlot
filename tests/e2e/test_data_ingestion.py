"""E2E tests for medical data ingestion."""

import tempfile
from pathlib import Path

from src.core.settings import Settings
from src.ingestion.pipeline import IngestionPipeline


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


class TestDataIngestion:
    """Test end-to-end data ingestion."""

    def test_ingest_single_document(self):
        """Test ingesting a single medical document."""
        fake_store = FakeVectorStore()
        settings = Settings()

        pipeline = IngestionPipeline(
            settings=settings,
            vector_store=fake_store,
            embedding_client=FakeEmbedding(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test document
            doc_path = Path(tmpdir) / "diabetes.txt"
            doc_path.write_text(
                "Diabetes Overview\n\n"
                "Diabetes is a chronic metabolic disorder.\n\n"
                "Clinical manifestations include increased thirst, "
                "frequent urination, and elevated blood glucose."
            )

            result = pipeline.run(tmpdir)

            assert result.total_files == 1
            assert result.processed_files == 1
            assert result.failed_files == 0
            assert result.total_chunks >= 1
            assert len(fake_store.upserted) >= 1

    def test_ingest_multiple_documents(self):
        """Test ingesting multiple documents."""
        fake_store = FakeVectorStore()
        settings = Settings()

        pipeline = IngestionPipeline(
            settings=settings,
            vector_store=fake_store,
            embedding_client=FakeEmbedding(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple test documents
            (Path(tmpdir) / "hypertension.txt").write_text(
                "Hypertension\n\nHigh blood pressure management."
            )
            (Path(tmpdir) / "asthma.txt").write_text(
                "Asthma\n\nRespiratory condition treatment."
            )
            (Path(tmpdir) / "arthritis.md").write_text(
                "# Arthritis\n\nJoint inflammation management."
            )

            result = pipeline.run(tmpdir)

            assert result.total_files == 3
            assert result.processed_files == 3
            assert result.failed_files == 0

    def test_ingest_with_collection(self):
        """Test ingestion with collection parameter."""
        fake_store = FakeVectorStore()
        settings = Settings()

        pipeline = IngestionPipeline(
            settings=settings,
            vector_store=fake_store,
            embedding_client=FakeEmbedding(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "test.txt"
            doc_path.write_text("Test content for collection.")

            result = pipeline.run(tmpdir, collection="medical_knowledge")

            assert result.processed_files == 1
            assert result.failed_files == 0

    def test_ingest_force_reload(self):
        """Test force reload processes all files."""
        fake_store = FakeVectorStore()
        settings = Settings()

        pipeline = IngestionPipeline(
            settings=settings,
            vector_store=fake_store,
            embedding_client=FakeEmbedding(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "test.txt"
            doc_path.write_text("Test content.")

            # First run
            result1 = pipeline.run(tmpdir, force=False)
            assert result1.processed_files == 1

            # Second run without force should skip
            result2 = pipeline.run(tmpdir, force=False)
            assert result2.skipped_files == 1

            # Force reload should process again
            result3 = pipeline.run(tmpdir, force=True)
            assert result3.processed_files == 1

    def test_ingest_nested_directories(self):
        """Test ingesting documents in nested directories."""
        fake_store = FakeVectorStore()
        settings = Settings()

        pipeline = IngestionPipeline(
            settings=settings,
            vector_store=fake_store,
            embedding_client=FakeEmbedding(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            subdir = Path(tmpdir) / "subdir" / "nested"
            subdir.mkdir(parents=True)

            (Path(tmpdir) / "root.txt").write_text("Root content")
            (subdir / "nested.txt").write_text("Nested content")

            result = pipeline.run(tmpdir)

            assert result.total_files == 2
            assert result.processed_files == 2
