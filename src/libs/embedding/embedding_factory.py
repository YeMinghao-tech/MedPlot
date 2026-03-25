"""Embedding Factory for creating Embedding instances based on configuration."""

from typing import Dict, Type

from src.core.settings import Settings
from src.libs.embedding.base_embedding import BaseEmbedding
from src.libs.embedding.dashscope_embedding import DashScopeEmbedding
from src.libs.embedding.ollama_embedding import OllamaEmbedding
from src.libs.embedding.openai_embedding import OpenAIEmbedding


class EmbeddingFactory:
    """Factory for creating Embedding instances based on configuration."""

    _providers: Dict[str, Type[BaseEmbedding]] = {
        "dashscope": DashScopeEmbedding,
        "openai": OpenAIEmbedding,
        "ollama": OllamaEmbedding,
    }

    @classmethod
    def create(cls, settings: Settings) -> BaseEmbedding:
        """Create an Embedding instance based on settings.

        Args:
            settings: Settings object containing Embedding configuration.

        Returns:
            An instance of a BaseEmbedding subclass.

        Raises:
            ValueError: If the provider is not supported.
        """
        provider = settings.embedding.provider.lower()
        model = settings.embedding.model

        if provider not in cls._providers:
            raise ValueError(
                f"Unsupported Embedding provider: {provider}. "
                f"Supported providers: {list(cls._providers.keys())}"
            )

        embed_class = cls._providers[provider]
        return embed_class(model=model)

    @classmethod
    def register_provider(cls, name: str, embed_class: Type[BaseEmbedding]) -> None:
        """Register a new Embedding provider.

        Args:
            name: Provider name (e.g., 'dashscope', 'openai').
            embed_class: The Embedding class to register.
        """
        cls._providers[name.lower()] = embed_class
