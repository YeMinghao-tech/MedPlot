"""Text document loader for .txt and .md files."""

import hashlib
from pathlib import Path
from typing import Optional

from src.core.types import Document
from src.libs.loader.base_loader import BaseLoader


class TextLoader(BaseLoader):
    """Loader for plain text (.txt) and Markdown (.md) files."""

    SUPPORTED_EXTENSIONS = {".txt", ".md"}

    def load(self, path: str) -> Document:
        """Load a text or markdown file.

        Args:
            path: Path to the file.

        Returns:
            A Document object with the file content.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file extension is not supported.
        """
        p = Path(path)

        if not p.exists():
            raise FileNotFoundError(f"File not found: {path}")

        suffix = p.suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file extension: {suffix}. "
                f"Supported: {self.SUPPORTED_EXTENSIONS}"
            )

        with open(p, "r", encoding="utf-8") as f:
            text = f.read()

        # Generate document ID from content hash
        doc_id = hashlib.sha256(text.encode()).hexdigest()[:16]

        # Extract metadata
        metadata = self._extract_metadata(path)
        metadata["file_size"] = p.stat().st_size

        # Extract title from first line if markdown
        if suffix == ".md":
            title = self._extract_title(text)
            if title:
                metadata["title"] = title

        return Document(
            doc_id=doc_id,
            text=text,
            metadata=metadata,
            source_ref=str(p.absolute()),
        )

    def _extract_title(self, text: str) -> Optional[str]:
        """Extract title from markdown content.

        Args:
            text: Markdown text content.

        Returns:
            Title if found, None otherwise.
        """
        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return None
