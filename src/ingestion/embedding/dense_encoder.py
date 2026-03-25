"""Dense encoder for generating dense vectors from chunks."""

from typing import Any, Dict, List, Optional

from src.core.types import Chunk
from src.libs.embedding.base_embedding import BaseEmbedding


class DenseEncoder:
    """Encodes chunks into dense vectors using an embedding model."""

    def __init__(self, embedding_client: BaseEmbedding):
        """Initialize the dense encoder.

        Args:
            embedding_client: Embedding client for generating vectors.
        """
        self.embedding_client = embedding_client

    def encode(self, chunks: List[Chunk]) -> List[List[float]]:
        """Encode chunks into dense vectors.

        Args:
            chunks: List of chunks to encode.

        Returns:
            List of dense vectors, one per chunk.
        """
        if not chunks:
            return []

        # Extract texts from chunks
        texts = [chunk.text for chunk in chunks]

        # Generate embeddings
        embeddings = self.embedding_client.embed(texts)

        return embeddings

    def encode_single(self, chunk: Chunk) -> List[float]:
        """Encode a single chunk.

        Args:
            chunk: Chunk to encode.

        Returns:
            Dense vector.
        """
        embeddings = self.encode([chunk])
        return embeddings[0] if embeddings else []
