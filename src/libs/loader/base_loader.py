"""Base Loader interface for document loading."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from src.core.types import Document


class BaseLoader(ABC):
    """Abstract base class for document loaders."""

    @abstractmethod
    def load(self, path: str) -> Document:
        """Load a document from path.

        Args:
            path: Path to the document file.

        Returns:
            A Document object with the loaded content.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file format is not supported.
        """
        pass

    def _extract_metadata(self, path: str) -> dict:
        """Extract basic metadata from file path.

        Args:
            path: Path to the file.

        Returns:
            Dictionary with metadata.
        """
        p = Path(path)
        return {
            "file_name": p.name,
            "file_path": str(p.absolute()),
            "file_extension": p.suffix.lower(),
        }
