"""Recursive Character Text Splitter implementation."""

import re
from typing import List

from src.libs.splitter.base_splitter import BaseSplitter


class RecursiveSplitter(BaseSplitter):
    """Recursive character text splitter that respects boundary characters."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: List[str] = None,
    ):
        """Initialize RecursiveSplitter.

        Args:
            chunk_size: Maximum chunk size in characters.
            chunk_overlap: Number of overlapping characters between chunks.
            separators: List of separator strings (in priority order).
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or [
            "\n\n",  # Paragraph break
            "\n",    # Line break
            "。",    # Chinese period
            "！",
            "？",
            "；",
            "，",
            " ",     # Space
            "",      # No separator - split by size
        ]

    def split_text(self, text: str, **kwargs) -> List[str]:
        """Split text into chunks using recursive character splitting.

        Args:
            text: The text to split.
            **kwargs: Additional parameters (chunk_size, chunk_overlap).

        Returns:
            List of text chunks.
        """
        chunk_size = kwargs.get("chunk_size", self.chunk_size)
        chunk_overlap = kwargs.get("chunk_overlap", self.chunk_overlap)

        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")

        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # If not at the end, try to break at a separator
            if end < len(text):
                # Find the best separator in the chunk
                split_pos = self._find_split_point(chunk, self.separators)
                if split_pos > 0:
                    chunk = chunk[:split_pos]
                    end = start + split_pos

            # Clean up the chunk
            chunk = chunk.strip()
            if chunk:
                chunks.append(chunk)

            # Move start with overlap
            start = end - chunk_overlap
            if start < 0:
                start = 0

        return chunks

    def _find_split_point(self, text: str, separators: List[str]) -> int:
        """Find the best position to split text."""
        for sep in separators:
            if not sep:
                continue
            # Find the last occurrence of separator in text
            pos = text.rfind(sep)
            if pos > len(text) // 4:  # Only split if separator is in latter portion
                return pos
        return -1

    def get_config(self) -> dict:
        """Return the splitter configuration."""
        return {
            "type": "recursive",
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "separators": self.separators,
        }
