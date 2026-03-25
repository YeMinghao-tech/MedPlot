"""Base VectorStore interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseVectorStore(ABC):
    """Abstract base class for VectorStore providers."""

    @abstractmethod
    def upsert(
        self,
        records: List[Dict[str, Any]],
        collection: str = "default",
        **kwargs
    ) -> None:
        """Insert or update records in the vector store.

        Args:
            records: List of records with 'id', 'embedding', and 'metadata' keys.
            collection: Collection name.
            **kwargs: Additional provider-specific parameters.
        """
        pass

    @abstractmethod
    def query(
        self,
        vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        collection: str = "default",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Query the vector store for similar records.

        Args:
            vector: Query embedding vector.
            top_k: Number of results to return.
            filters: Optional metadata filters.
            collection: Collection name.
            **kwargs: Additional provider-specific parameters.

        Returns:
            List of matching records with 'id', 'score', and 'metadata'.
        """
        pass

    @abstractmethod
    def get_by_ids(
        self, ids: List[str], collection: str = "default", **kwargs
    ) -> List[Dict[str, Any]]:
        """Get records by their IDs.

        Args:
            ids: List of record IDs.
            collection: Collection name.
            **kwargs: Additional parameters.

        Returns:
            List of records.
        """
        pass

    @abstractmethod
    def delete_by_metadata(
        self,
        filter: Dict[str, Any],
        collection: str = "default",
        **kwargs
    ) -> None:
        """Delete records by metadata filter.

        Args:
            filter: Metadata filter conditions.
            collection: Collection name.
            **kwargs: Additional parameters.
        """
        pass
