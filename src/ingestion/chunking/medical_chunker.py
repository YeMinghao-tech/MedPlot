"""Medical chunker for semantic text splitting.

Uses the splitter abstraction layer with medical-specific separators.
"""

from typing import List

from src.core.types import Chunk, Document
from src.libs.splitter.base_splitter import BaseSplitter
from src.libs.splitter.splitter_factory import SplitterFactory


class MedicalChunker:
    """Medical document chunker.

    Splits documents into semantic chunks while preserving medical section boundaries
    like "疾病概述", "临床表现", "治疗原则".
    """

    # Medical section separators (in priority order)
    MEDICAL_SEPARATORS = [
        "\n## ",      # Markdown H2 sections
        "\n# ",       # Markdown H1 sections
        "\n### ",     # Markdown H3 sections
        "疾病概述",    # Disease overview
        "临床表现",    # Clinical manifestations
        "诊断标准",    # Diagnostic criteria
        "治疗原则",    # Treatment principles
        "用药指导",    # Medication guide
        "注意事项",    # Precautions
        "\n\n",       # Paragraph breaks
        "\n",         # Line breaks
    ]

    def __init__(self, splitter: BaseSplitter = None):
        """Initialize the medical chunker.

        Args:
            splitter: Text splitter to use. If None, uses default from factory.
        """
        self.splitter = splitter or SplitterFactory.create_default()

    def split_document(self, document: Document, **kwargs) -> List[Chunk]:
        """Split a document into medical semantic chunks.

        Args:
            document: Document to split.
            **kwargs: Additional parameters (chunk_size, overlap).

        Returns:
            List of Chunk objects.
        """
        chunks = []
        texts = self.splitter.split_text(document.text, **kwargs)

        for i, text in enumerate(texts):
            # Generate stable chunk ID
            chunk_id = self._generate_chunk_id(document.doc_id, i, text)

            # Determine medical section from content
            section = self._detect_medical_section(text)

            chunk = Chunk(
                chunk_id=chunk_id,
                text=text,
                metadata={
                    **document.metadata,
                    "section": section,
                    "parent_doc_id": document.doc_id,
                },
                source_ref=document.source_ref,
                chunk_index=i,
            )
            chunks.append(chunk)

        return chunks

    def _generate_chunk_id(self, doc_id: str, index: int, text: str) -> str:
        """Generate a stable chunk ID.

        Args:
            doc_id: Parent document ID.
            index: Chunk index.
            text: Chunk text content.

        Returns:
            Stable chunk ID string.
        """
        import hashlib

        # Use doc_id + index + first 50 chars for stable ID
        content_prefix = text[:50].encode().decode("utf-8", errors="ignore")
        id_input = f"{doc_id}_{index}_{content_prefix}"
        return hashlib.sha256(id_input.encode()).hexdigest()[:20]

    def _detect_medical_section(self, text: str) -> str:
        """Detect the medical section type from chunk text.

        Args:
            text: Chunk text.

        Returns:
            Section type string.
        """
        for separator in self.MEDICAL_SEPARATORS:
            if separator in text:
                # Return the separator found (cleaned up)
                return separator.strip()
        return "general"


class DefaultSplitterFactory:
    """Helper to create default splitter with medical settings."""

    @staticmethod
    def create_default_splitter() -> BaseSplitter:
        """Create a default splitter configured for medical text.

        Returns:
            BaseSplitter instance.
        """
        from src.libs.splitter.recursive_splitter import RecursiveSplitter

        return RecursiveSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=MedicalChunker.MEDICAL_SEPARATORS,
        )
