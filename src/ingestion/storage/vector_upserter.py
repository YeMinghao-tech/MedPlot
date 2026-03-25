"""Vector upsert for idempotent vector storage."""

import hashlib
from typing import Any, Dict, List, Optional

from src.core.types import Chunk, ChunkRecord
from src.libs.vector_store.base_vector_store import BaseVectorStore


class VectorUpserter:
    """Handles idempotent upsert of chunk vectors to vector store.

    Ensures stable chunk_id generation and prevents duplicate records.
    """

    def __init__(self, vector_store: BaseVectorStore):
        """Initialize the vector upsert.

        Args:
            vector_store: Vector store for persistence.
        """
        self.vector_store = vector_store

    def upsert(
        self,
        chunks: List[Chunk],
        dense_embeddings: List[List[float]],
        collection: str = "default",
    ) -> List[str]:
        """Idempotently upsert chunks to vector store.

        Args:
            chunks: List of chunks to upsert.
            dense_embeddings: Dense embeddings for each chunk.
            collection: Collection name.

        Returns:
            List of chunk IDs that were upserted.
        """
        if not chunks or not dense_embeddings:
            return []

        if len(chunks) != len(dense_embeddings):
            raise ValueError(
                f"Number of chunks ({len(chunks)}) must match "
                f"number of embeddings ({len(dense_embeddings)})"
            )

        records = []
        chunk_ids = []

        for i, chunk in enumerate(chunks):
            chunk_id = self._generate_stable_id(chunk, dense_embeddings[i])
            chunk_ids.append(chunk_id)

            record = {
                "id": chunk_id,
                "text": chunk.text,
                "embedding": dense_embeddings[i],
                "metadata": {
                    **chunk.metadata,
                    "source_ref": chunk.source_ref,
                    "chunk_index": chunk.chunk_index,
                },
            }
            records.append(record)

        # Upsert to vector store
        self.vector_store.upsert(records, collection=collection)

        return chunk_ids

    def _generate_stable_id(self, chunk: Chunk, embedding: List[float]) -> str:
        """Generate a stable chunk ID.

        The ID is derived from content hash + embedding hash to ensure
        same content always produces same ID.

        Args:
            chunk: Chunk to generate ID for.
            embedding: Dense embedding vector.

        Returns:
            Stable chunk ID string.
        """
        # Use content + first few embedding dims for stable ID
        content_hash = hashlib.sha256(chunk.text.encode()).hexdigest()[:16]
        emb_hash = hashlib.sha256(
            str(embedding[:10]).encode()
        ).hexdigest()[:8]
        return f"chunk_{content_hash}_{emb_hash}"

    def upsert_records(
        self,
        chunk_records: List[ChunkRecord],
        collection: str = "default",
    ) -> List[str]:
        """Idempotently upsert ChunkRecords to vector store.

        Args:
            chunk_records: List of ChunkRecords to upsert.
            collection: Collection name.

        Returns:
            List of chunk IDs that were upserted.
        """
        if not chunk_records:
            return []

        records = []
        chunk_ids = []

        for record in chunk_records:
            chunk_ids.append(record.chunk.chunk_id)

            vector_record = record.to_vector_record()
            records.append(vector_record)

        self.vector_store.upsert(records, collection=collection)

        return chunk_ids
