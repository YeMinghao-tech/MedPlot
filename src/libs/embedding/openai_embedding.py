"""OpenAI Embedding implementation."""

from typing import List, Optional

from src.libs.embedding.base_embedding import BaseEmbedding


class OpenAIEmbedding(BaseEmbedding):
    """OpenAI Embedding implementation."""

    def __init__(
        self, model: str = "text-embedding-ada-002", api_key: Optional[str] = None
    ):
        """Initialize OpenAI Embedding.

        Args:
            model: Model name (default: text-embedding-ada-002).
            api_key: OpenAI API key. If None, uses environment variable.
        """
        self.model = model
        self.api_key = api_key
        self._dimension = 1536  # Default for ada-002

    def embed(self, texts: List[str], **kwargs) -> List[List[float]]:
        """Generate embeddings for texts using OpenAI API.

        Args:
            texts: List of text strings to embed.
            **kwargs: Additional parameters.

        Returns:
            List of embedding vectors.
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package is required for OpenAI Embedding. "
                "Install it with: pip install openai"
            )

        client_kwargs = {"api_key": self.api_key} if self.api_key else {}
        client = OpenAI(**client_kwargs)

        embeddings = []
        for text in texts:
            response = client.embeddings.create(model=self.model, input=text)
            embeddings.append(response.data[0].embedding)

        return embeddings

    def get_model_name(self) -> str:
        """Return the model name."""
        return self.model

    def get_dimension(self) -> int:
        """Return the embedding dimension."""
        return self._dimension
