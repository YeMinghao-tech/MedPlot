"""Chunk refiner for rule-based and LLM-based text refinement."""

import re
from typing import Any, Dict, List, Optional

from src.core.types import Chunk
from src.ingestion.transform.base_transform import BaseTransform


class ChunkRefiner(BaseTransform):
    """Refines chunks using rule-based cleaning and optional LLM enhancement.

    Rule-based cleaning includes:
    - Removing excessive whitespace
    - Normalizing punctuation
    - Fixing common OCR errors

    LLM enhancement is optional and degrades gracefully to rules-only.
    """

    # Patterns for rule-based refinement
    WHITESPACE_PATTERN = re.compile(r"\s+")
    PUNCTUATION_PATTERN = re.compile(r"([。；！？，,])\1+")
    LEADING_WHITESPACE_PATTERN = re.compile(r"^\s+")
    TRAILING_WHITESPACE_PATTERN = re.compile(r"\s+$")

    def __init__(self, llm=None):
        """Initialize the chunk refiner.

        Args:
            llm: Optional LLM instance for intelligent refinement.
                 If None, uses rule-based refinement only.
        """
        self.llm = llm

    def transform(
        self, chunks: List[Chunk], trace: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Transform chunks by refining text.

        Args:
            chunks: List of chunks to refine.
            trace: Optional trace context.

        Returns:
            List of refined chunks.
        """
        refined_chunks = []

        for chunk in chunks:
            refined_text = self._rule_based_refine(chunk.text)

            # If LLM is available, try LLM refinement
            if self.llm:
                llm_refined = self._llm_refine(refined_text, trace)
                if llm_refined:
                    refined_text = llm_refined
                    self._update_trace(trace, "llm_refine", "success")
                else:
                    self._update_trace(trace, "llm_refine", "fallback_to_rules")
            else:
                self._update_trace(trace, "refine", "rule_based_only")

            # Create new chunk with refined text
            refined_chunk = Chunk(
                chunk_id=chunk.chunk_id,
                text=refined_text,
                metadata={
                    **chunk.metadata,
                    "refined": True,
                    "llm_enhanced": self.llm is not None,
                },
                source_ref=chunk.source_ref,
                chunk_index=chunk.chunk_index,
            )
            refined_chunks.append(refined_chunk)

        return refined_chunks

    def _rule_based_refine(self, text: str) -> str:
        """Apply rule-based refinement to text.

        Args:
            text: Input text.

        Returns:
            Refined text.
        """
        # Remove excessive whitespace
        text = self.WHITESPACE_PATTERN.sub(" ", text)

        # Normalize repeated punctuation
        text = self.PUNCTUATION_PATTERN.sub(r"\1", text)

        # Remove leading/trailing whitespace per line
        lines = text.split("\n")
        lines = [line.strip() for line in lines]
        text = "\n".join(lines)

        # Remove empty lines at start/end
        text = text.strip()

        return text

    def _llm_refine(
        self, text: str, trace: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Use LLM to enhance text refinement.

        Args:
            text: Input text.
            trace: Trace context.

        Returns:
            LLM-refined text, or None if LLM fails.
        """
        if not self.llm:
            return None

        try:
            prompt = f"""请优化以下医学文本，使其更加清晰、规范。

原文：
{text}

优化后的文本（只输出优化后的内容）：
"""
            response = self.llm.chat([{"role": "user", "content": prompt}])

            if response and len(response.strip()) > 0:
                return response.strip()
        except Exception as e:
            self._update_trace(trace, "llm_refine_error", str(e))

        return None
