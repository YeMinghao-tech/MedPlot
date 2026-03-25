"""DashScope (Alibaba Cloud) Embedding implementation."""

from typing import List, Optional

from src.libs.embedding.base_embedding import BaseEmbedding


class DashScopeEmbedding(BaseEmbedding):
    """DashScope Embedding implementation using text-embedding API."""

    def __init__(self, model: str = "text-embedding-v1"):
        """Initialize DashScope Embedding.

        Args:
            model: Model name (default: text-embedding-v1).
        """
        self.model = model
        self._dimension = 1536  # Default dimension for text-embedding-v1

    def embed(self, texts: List[str], **kwargs) -> List[List[float]]:
        """Generate embeddings for texts using DashScope API.

        Args:
            texts: List of text strings to embed.
            **kwargs: Additional parameters (batch_size, etc.)

        Returns:
            List of embedding vectors.
        """
        try:
            import dashscope
            from dashscope import TextEmbedding
        except ImportError:
            raise ImportError(
                "dashscope package is required for DashScope Embedding. "
                "Install it with: pip install dashscope"
            )

        # Check for API key
        import os

        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if api_key:
            dashscope.api_key = api_key

        embeddings = []
        for text in texts:
            response = TextEmbedding.call(model=self.model, text=text)
            if response.status_code != 200:
                raise RuntimeError(
                    f"DashScope Embedding API error: {response.code} - {response.message}"
                )
            embeddings.append(response.output.embeddings[0].embedding)

        return embeddings

    def get_model_name(self) -> str:
        """Return the model name."""
        return self.model

    def get_dimension(self) -> int:
        """Return the embedding dimension."""
        return self._dimension
