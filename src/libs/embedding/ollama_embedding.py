"""Ollama Embedding implementation."""

from typing import List, Optional

from src.libs.embedding.base_embedding import BaseEmbedding


class OllamaEmbedding(BaseEmbedding):
    """Ollama Embedding implementation for local models."""

    def __init__(
        self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434"
    ):
        """Initialize Ollama Embedding.

        Args:
            model: Model name (default: nomic-embed-text).
            base_url: Base URL for Ollama API.
        """
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._dimension = 768  # Default dimension, varies by model

    def embed(self, texts: List[str], **kwargs) -> List[List[float]]:
        """Generate embeddings for texts using Ollama API.

        Args:
            texts: List of text strings to embed.
            **kwargs: Additional parameters.

        Returns:
            List of embedding vectors.
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx package is required for Ollama Embedding. "
                "Install it with: pip install httpx"
            )

        embeddings = []
        with httpx.Client(timeout=120.0) as client:
            for text in texts:
                response = client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model, "input": text},
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data.get("embeddings", [[]])[0])

        return embeddings

    def get_model_name(self) -> str:
        """Return the model name."""
        return self.model

    def get_dimension(self) -> int:
        """Return the embedding dimension."""
        return self._dimension
