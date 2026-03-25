"""Splitter Factory for creating Splitter instances based on configuration."""

from typing import Dict, Type

from src.core.settings import Settings
from src.libs.splitter.base_splitter import BaseSplitter
from src.libs.splitter.recursive_splitter import RecursiveSplitter


class SplitterFactory:
    """Factory for creating Splitter instances based on configuration."""

    _providers: Dict[str, Type[BaseSplitter]] = {
        "recursive": RecursiveSplitter,
    }

    @classmethod
    def create(cls, settings: Settings) -> BaseSplitter:
        """Create a Splitter instance based on settings.

        Args:
            settings: Settings object containing Splitter configuration.

        Returns:
            An instance of a BaseSplitter subclass.

        Raises:
            ValueError: If the provider is not supported.
        """
        # Splitter config comes from retrieval section or a dedicated section
        # Default to recursive if not specified
        provider = getattr(settings.retrieval, "splitter_backend", "recursive")
        provider = provider.lower()

        if provider not in cls._providers:
            raise ValueError(
                f"Unsupported Splitter provider: {provider}. "
                f"Supported providers: {list(cls._providers.keys())}"
            )

        splitter_class = cls._providers[provider]
        return splitter_class()

    @classmethod
    def register_provider(cls, name: str, splitter_class: Type[BaseSplitter]) -> None:
        """Register a new Splitter provider.

        Args:
            name: Provider name (e.g., 'recursive').
            splitter_class: The Splitter class to register.
        """
        cls._providers[name.lower()] = splitter_class

    @classmethod
    def create_default(cls) -> BaseSplitter:
        """Create a default splitter with reasonable settings.

        Returns:
            A RecursiveSplitter with default medical-friendly settings.
        """
        return RecursiveSplitter(chunk_size=500, chunk_overlap=50)
