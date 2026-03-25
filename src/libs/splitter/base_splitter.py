"""Base Splitter interface."""

from abc import ABC, abstractmethod
from typing import List


class BaseSplitter(ABC):
    """Abstract base class for text splitters."""

    @abstractmethod
    def split_text(self, text: str, **kwargs) -> List[str]:
        """Split text into chunks.

        Args:
            text: The text to split.
            **kwargs: Additional provider-specific parameters
                       (e.g., chunk_size, overlap).

        Returns:
            List of text chunks.
        """
        pass

    @abstractmethod
    def get_config(self) -> dict:
        """Return the splitter configuration."""
        pass
