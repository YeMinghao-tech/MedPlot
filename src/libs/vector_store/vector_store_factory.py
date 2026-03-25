"""VectorStore Factory for creating VectorStore instances based on configuration."""

from typing import Dict, Type

from src.core.settings import Settings
from src.libs.vector_store.base_vector_store import BaseVectorStore
from src.libs.vector_store.chroma_store import ChromaStore


class VectorStoreFactory:
    """Factory for creating VectorStore instances based on configuration."""

    _providers: Dict[str, Type[BaseVectorStore]] = {
        "chroma": ChromaStore,
    }

    @classmethod
    def create(cls, settings: Settings) -> BaseVectorStore:
        """Create a VectorStore instance based on settings.

        Args:
            settings: Settings object containing VectorStore configuration.

        Returns:
            An instance of a BaseVectorStore subclass.

        Raises:
            ValueError: If the provider is not supported.
        """
        provider = settings.vector_store.backend.lower()
        persist_path = settings.vector_store.persist_path

        if provider not in cls._providers:
            raise ValueError(
                f"Unsupported VectorStore provider: {provider}. "
                f"Supported providers: {list(cls._providers.keys())}"
            )

        store_class = cls._providers[provider]

        # Provider-specific initialization
        if provider == "chroma":
            return store_class(persist_path=persist_path)
        else:
            return store_class()

    @classmethod
    def register_provider(
        cls, name: str, store_class: Type[BaseVectorStore]
    ) -> None:
        """Register a new VectorStore provider.

        Args:
            name: Provider name (e.g., 'chroma').
            store_class: The VectorStore class to register.
        """
        cls._providers[name.lower()] = store_class
