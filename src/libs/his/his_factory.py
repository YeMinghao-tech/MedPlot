"""HIS Factory for creating HIS client instances based on configuration."""

from src.core.settings import Settings
from src.libs.his.base_his import BaseHISClient
from src.libs.his.mock_his import MockHISClient


class HISFactory:
    """Factory for creating HIS client instances based on configuration."""

    _providers = {
        "mock": MockHISClient,
    }

    @classmethod
    def create(cls, settings: Settings) -> BaseHISClient:
        """Create a HIS client instance based on settings.

        Args:
            settings: Settings object containing HIS configuration.

        Returns:
            An instance of a BaseHISClient subclass.

        Raises:
            ValueError: If the provider is not supported.
        """
        backend = settings.his.backend.lower()

        if backend not in cls._providers:
            raise ValueError(
                f"Unsupported HIS backend: {backend}. "
                f"Supported backends: {list(cls._providers.keys())}"
            )

        client_class = cls._providers[backend]

        if backend == "mock":
            return client_class(db_path=settings.his.mock_db_path, use_wal=settings.his.use_wal)
        else:
            return client_class()

    @classmethod
    def register_provider(cls, name: str, client_class) -> None:
        """Register a new HIS provider.

        Args:
            name: Provider name (e.g., 'mock').
            client_class: The HIS client class to register.
        """
        cls._providers[name.lower()] = client_class
