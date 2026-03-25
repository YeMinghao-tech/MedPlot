"""Core data types for the ingestion pipeline.

Defines Document, Chunk, and ChunkRecord types used throughout the system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Document:
    """Represents a source document for ingestion.

    Attributes:
        doc_id: Unique document identifier.
        text: Full text content.
        metadata: Document-level metadata.
        source_ref: Reference to the source file/path.
    """

    doc_id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_ref: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "doc_id": self.doc_id,
            "text": self.text,
            "metadata": self.metadata,
            "source_ref": self.source_ref,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        """Create from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        return cls(
            doc_id=data["doc_id"],
            text=data["text"],
            metadata=data.get("metadata", {}),
            source_ref=data.get("source_ref"),
            created_at=created_at or datetime.now(),
        )


@dataclass
class Chunk:
    """Represents a chunk split from a document.

    Attributes:
        chunk_id: Unique chunk identifier.
        text: Chunk text content.
        metadata: Chunk-level metadata.
        source_ref: Reference to the source document.
        chunk_index: Position of this chunk in the document.
    """

    chunk_id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_ref: Optional[str] = None
    chunk_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "metadata": self.metadata,
            "source_ref": self.source_ref,
            "chunk_index": self.chunk_index,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        """Create from dictionary."""
        return cls(
            chunk_id=data["chunk_id"],
            text=data["text"],
            metadata=data.get("metadata", {}),
            source_ref=data.get("source_ref"),
            chunk_index=data.get("chunk_index", 0),
        )


@dataclass
class ChunkRecord:
    """Represents a chunk with its vector embeddings for storage.

    Used when storing chunks in the vector store.

    Attributes:
        chunk: The underlying chunk data.
        dense_embedding: Dense vector from embedding model.
        sparse_embedding: Sparse vector for BM25.
        authority_level: Medical authority level (1-5, higher = more authoritative).
        disease_tags: Extracted disease tags.
    """

    chunk: Chunk
    dense_embedding: List[float] = field(default_factory=list)
    sparse_embedding: Dict[str, float] = field(default_factory=dict)
    authority_level: int = 1
    disease_tags: List[str] = field(default_factory=list)
    image_refs: List[str] = field(default_factory=list)
    has_unprocessed_images: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        result = self.chunk.to_dict()
        result.update({
            "dense_embedding": self.dense_embedding,
            "sparse_embedding": self.sparse_embedding,
            "authority_level": self.authority_level,
            "disease_tags": self.disease_tags,
            "image_refs": self.image_refs,
            "has_unprocessed_images": self.has_unprocessed_images,
        })
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChunkRecord":
        """Create from dictionary."""
        return cls(
            chunk=Chunk.from_dict(data),
            dense_embedding=data.get("dense_embedding", []),
            sparse_embedding=data.get("sparse_embedding", {}),
            authority_level=data.get("authority_level", 1),
            disease_tags=data.get("disease_tags", []),
            image_refs=data.get("image_refs", []),
            has_unprocessed_images=data.get("has_unprocessed_images", False),
        )

    def to_vector_record(self) -> Dict[str, Any]:
        """Convert to vector store record format."""
        return {
            "id": self.chunk.chunk_id,
            "text": self.chunk.text,
            "embedding": self.dense_embedding,
            "metadata": {
                "source_ref": self.chunk.source_ref,
                "chunk_index": self.chunk.chunk_index,
                "authority_level": self.authority_level,
                "disease_tags": self.disease_tags,
                **self.chunk.metadata,
            },
        }
