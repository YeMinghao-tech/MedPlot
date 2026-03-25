"""Ingestion pipeline for medical knowledge base."""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.core.settings import Settings
from src.core.types import Chunk, ChunkRecord, Document
from src.ingestion.chunking.medical_chunker import MedicalChunker
from src.ingestion.embedding.dense_encoder import DenseEncoder
from src.ingestion.embedding.sparse_encoder import SparseEncoder
from src.ingestion.storage.bm25_indexer import BM25Indexer
from src.ingestion.storage.vector_upserter import VectorUpserter
from src.ingestion.transform.chunk_refiner import ChunkRefiner
from src.ingestion.transform.image_captioner import ImageCaptioner
from src.ingestion.transform.metadata_enricher import MetadataEnricher
from src.libs.embedding.base_embedding import BaseEmbedding
from src.libs.loader.file_integrity import SQLiteIntegrityChecker
from src.libs.loader.text_loader import TextLoader
from src.libs.vector_store.base_vector_store import BaseVectorStore


@dataclass
class IngestionResult:
    """Result of an ingestion operation."""

    total_files: int = 0
    processed_files: int = 0
    skipped_files: int = 0
    failed_files: int = 0
    total_chunks: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)


class IngestionPipeline:
    """Pipeline for ingesting medical documents.

    Stages:
    1. Load: Load documents from files
    2. Split: Split documents into chunks
    3. Transform: Refine and enrich chunks
    4. Embed: Generate dense and sparse embeddings
    5. Upsert: Store in vector store and BM25 index
    """

    def __init__(
        self,
        settings: Settings,
        vector_store: BaseVectorStore,
        embedding_client: BaseEmbedding,
        on_progress: Optional[Callable[[str, int, int], None]] = None,
    ):
        """Initialize the ingestion pipeline.

        Args:
            settings: Application settings.
            vector_store: Vector store for embedding persistence.
            embedding_client: Embedding client for dense vectors.
            on_progress: Optional progress callback (stage, current, total).
        """
        self.settings = settings
        self.vector_store = vector_store
        self.embedding_client = embedding_client

        # Initialize components
        self.integrity_checker = SQLiteIntegrityChecker()
        self.text_loader = TextLoader()
        self.chunker = MedicalChunker()
        self.refiner = ChunkRefiner()
        self.enricher = MetadataEnricher()
        self.captioner = ImageCaptioner()
        self.dense_encoder = DenseEncoder(embedding_client)
        self.sparse_encoder = SparseEncoder()
        self.vector_upserter = VectorUpserter(vector_store)

        self.on_progress = on_progress

    def run(
        self,
        source_path: str,
        collection: str = "default",
        force: bool = False,
    ) -> IngestionResult:
        """Run the ingestion pipeline.

        Args:
            source_path: Path to source documents.
            collection: Collection name for the vector store.
            force: If True, re-process all files regardless of changes.

        Returns:
            IngestionResult with statistics.
        """
        start_time = time.time()
        result = IngestionResult()

        # Find all text files
        files = list(Path(source_path).rglob("*.txt")) + list(Path(source_path).rglob("*.md"))
        result.total_files = len(files)

        self._report_progress("discover", 0, result.total_files)

        # Process each file
        all_chunks: List[Chunk] = []

        for i, file_path in enumerate(files):
            file_str = str(file_path)

            # Check integrity
            if not force and self.integrity_checker.should_skip(file_str):
                result.skipped_files += 1
                self._report_progress("load", i + 1, result.total_files)
                continue

            try:
                # Stage 1: Load
                doc = self.text_loader.load(file_str)
                self._report_progress("load", i + 1, result.total_files)

                # Stage 2: Split
                chunks = self.chunker.split_document(doc)
                self._report_progress("split", i + 1, result.total_files)

                # Stage 3: Transform
                chunks = self.refiner.transform(chunks)
                chunks = self.enricher.transform(chunks)
                chunks = self.captioner.transform(chunks)
                self._report_progress("transform", i + 1, result.total_files)

                all_chunks.extend(chunks)
                result.processed_files += 1

                # Mark as success
                self.integrity_checker.mark_success(file_str)

            except Exception as e:
                result.failed_files += 1
                result.errors.append(f"{file_str}: {str(e)}")
                self.integrity_checker.mark_failed(file_str, str(e))

            self._report_progress("process", i + 1, result.total_files)

        # Stage 4 & 5: Embed and Upsert
        if all_chunks:
            self._embed_and_upsert(all_chunks, collection)

        result.total_chunks = len(all_chunks)
        result.duration_seconds = time.time() - start_time

        return result

    def _embed_and_upsert(self, chunks: List[Chunk], collection: str) -> None:
        """Embed chunks and upsert to storage.

        Args:
            chunks: List of chunks to process.
            collection: Collection name.
        """
        # Generate embeddings
        dense_embeddings = self.dense_encoder.encode(chunks)

        # Upsert to vector store
        self.vector_upserter.upsert(chunks, dense_embeddings, collection=collection)

    def _report_progress(self, stage: str, current: int, total: int) -> None:
        """Report progress if callback is set."""
        if self.on_progress:
            self.on_progress(stage, current, total)
