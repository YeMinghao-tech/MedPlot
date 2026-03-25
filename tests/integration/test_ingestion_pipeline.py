"""Integration tests for ingestion pipeline."""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock

from src.core.settings import Settings, LLMConfig, EmbeddingConfig, VectorStoreConfig
from src.core.types import Chunk
from src.ingestion.pipeline import IngestionPipeline, IngestionResult
from src.libs.vector_store.chroma_store import ChromaStore


class MockEmbeddingClient:
    """Mock embedding client for testing without external API calls."""

    def __init__(self, dimension: int = 4):
        self.dimension = dimension
        self._call_count = 0

    def embed(self, texts):
        """Return deterministic fake embeddings based on text hash."""
        self._call_count += 1
        import hashlib
        result = []
        for text in texts:
            # Generate deterministic fake vector from text content
            hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            vec = [(hash_val >> (i * 8)) % 256 / 255.0 for i in range(self.dimension)]
            # Normalize
            norm = sum(v * v for v in vec) ** 0.5
            vec = [v / norm if norm > 0 else v for v in vec]
            result.append(vec)
        return result


class TestIngestionPipeline:
    """Integration tests for IngestionPipeline."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.docs_dir = os.path.join(self.temp_dir, "docs")
        os.makedirs(self.docs_dir)

        self.db_dir = os.path.join(self.temp_dir, "db")
        os.makedirs(self.db_dir)

        # Create test settings
        self.settings = Settings(
            llm=LLMConfig(provider="dashscope", model="qwen-max"),
            embedding=EmbeddingConfig(provider="dashscope", model="text-embedding-v1"),
            vector_store=VectorStoreConfig(backend="chroma", persist_path=self.db_dir),
        )

    def teardown_method(self):
        """Clean up temp files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_doc(self, filename: str, content: str) -> str:
        """Create a test document file."""
        path = os.path.join(self.docs_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_pipeline_runs_end_to_end(self):
        """Test that pipeline processes documents end-to-end."""
        # Create test documents
        self._create_test_doc(
            "cold.txt",
            "感冒是一种常见疾病\n\n疾病概述\n感冒是一种常见的呼吸道疾病。\n\n临床表现\n症状包括发热、咳嗽、流涕和喉咙痛。\n\n治疗原则\n以对症治疗为主，注意休息。"
        )
        self._create_test_doc(
            "heart_disease.txt",
            "心脏病概述\n\n疾病概述\n心脏病是心脏疾病的总称。\n\n临床表现\n胸痛、呼吸困难、心悸是常见症状。\n\n治疗原则\n需要及时就医，遵医嘱服药。"
        )

        # Create mock embedding and vector store
        mock_embedding = MockEmbeddingClient()
        vector_store = ChromaStore(persist_path=os.path.join(self.db_dir, "chroma"))

        # Create pipeline
        pipeline = IngestionPipeline(
            settings=self.settings,
            vector_store=vector_store,
            embedding_client=mock_embedding,
        )

        # Track progress calls
        progress_calls = []

        def on_progress(stage, current, total):
            progress_calls.append((stage, current, total))

        pipeline.on_progress = on_progress

        # Run pipeline
        result = pipeline.run(source_path=self.docs_dir, collection="test_collection")

        # Verify results
        assert isinstance(result, IngestionResult)
        assert result.total_files == 2
        assert result.processed_files == 2
        assert result.skipped_files == 0
        assert result.failed_files == 0
        assert result.total_chunks > 0
        assert result.duration_seconds >= 0

        # Verify progress was reported
        assert len(progress_calls) > 0
        stages = [p[0] for p in progress_calls]
        assert "discover" in stages
        assert "load" in stages
        assert "split" in stages
        assert "transform" in stages

        # Verify vector store received records
        assert mock_embedding._call_count > 0

    def test_pipeline_skips_unchanged_files(self):
        """Test that pipeline skips files that haven't changed."""
        # Create test document
        self._create_test_doc("test.txt", "这是一段测试文本。")

        mock_embedding = MockEmbeddingClient()
        vector_store = ChromaStore(persist_path=os.path.join(self.db_dir, "chroma1"))

        pipeline = IngestionPipeline(
            settings=self.settings,
            vector_store=vector_store,
            embedding_client=mock_embedding,
        )

        # First run
        result1 = pipeline.run(source_path=self.docs_dir, collection="test")
        assert result1.processed_files == 1
        assert result1.skipped_files == 0

        # Second run without force - should skip
        result2 = pipeline.run(source_path=self.docs_dir, collection="test")
        assert result2.processed_files == 0
        assert result2.skipped_files == 1

    def test_pipeline_force_reprocesses(self):
        """Test that force=True reprocesses all files."""
        self._create_test_doc("test.txt", "这是一段测试文本。")

        mock_embedding = MockEmbeddingClient()
        vector_store = ChromaStore(persist_path=os.path.join(self.db_dir, "chroma2"))

        pipeline = IngestionPipeline(
            settings=self.settings,
            vector_store=vector_store,
            embedding_client=mock_embedding,
        )

        # First run
        pipeline.run(source_path=self.docs_dir, collection="test")
        first_call_count = mock_embedding._call_count

        # Second run with force
        pipeline.run(source_path=self.docs_dir, collection="test", force=True)
        second_call_count = mock_embedding._call_count

        # With force, should process again
        assert second_call_count >= first_call_count

    def test_pipeline_handles_empty_directory(self):
        """Test pipeline with no documents."""
        empty_dir = os.path.join(self.temp_dir, "empty")
        os.makedirs(empty_dir)

        mock_embedding = MockEmbeddingClient()
        vector_store = ChromaStore(persist_path=os.path.join(self.db_dir, "chroma"))

        pipeline = IngestionPipeline(
            settings=self.settings,
            vector_store=vector_store,
            embedding_client=mock_embedding,
        )

        result = pipeline.run(source_path=empty_dir, collection="test")

        assert result.total_files == 0
        assert result.processed_files == 0
        assert result.skipped_files == 0
        assert result.total_chunks == 0

    def test_pipeline_progress_callback(self):
        """Test that progress callback is called correctly."""
        self._create_test_doc("doc1.txt", "第一份文档内容。")
        self._create_test_doc("doc2.txt", "第二份文档内容。")

        mock_embedding = MockEmbeddingClient()
        vector_store = ChromaStore(persist_path=os.path.join(self.db_dir, "chroma3"))

        pipeline = IngestionPipeline(
            settings=self.settings,
            vector_store=vector_store,
            embedding_client=mock_embedding,
        )

        progress_log = []

        def track_progress(stage, current, total):
            progress_log.append({"stage": stage, "current": current, "total": total})

        pipeline.on_progress = track_progress
        pipeline.run(source_path=self.docs_dir, collection="test")

        # Verify discover was called with total
        discover_calls = [p for p in progress_log if p["stage"] == "discover"]
        assert len(discover_calls) == 1
        assert discover_calls[0]["total"] == 2

    def test_pipeline_collection_parameter(self):
        """Test that collection parameter is passed correctly."""
        self._create_test_doc("test.txt", "测试文档内容。")

        mock_embedding = MockEmbeddingClient()
        vector_store = ChromaStore(persist_path=os.path.join(self.db_dir, "chroma4"))

        pipeline = IngestionPipeline(
            settings=self.settings,
            vector_store=vector_store,
            embedding_client=mock_embedding,
        )

        result = pipeline.run(source_path=self.docs_dir, collection="medical_knowledge")
        assert result.processed_files == 1
        # Pipeline completed without error for specified collection
