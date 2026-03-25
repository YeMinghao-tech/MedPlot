"""Metadata enricher for injecting medical metadata into chunks."""

import re
from typing import Any, Dict, List, Optional, Set

from src.core.types import Chunk
from src.ingestion.transform.base_transform import BaseTransform


class MetadataEnricher(BaseTransform):
    """Enriches chunks with medical metadata.

    Injects:
    - Disease tags (extracted from content)
    - Authority level (based on source type)
    - Medical keywords
    """

    # Common disease patterns
    DISEASE_PATTERNS = [
        r"([\u4e00-\u9fa5]{2,8})(?:病|症|炎|癌|瘤|炎|热|痛|病|综合征)",
        r"(感冒|发烧|发热|咳嗽|哮喘|肺炎|胃炎|肠炎|肝炎|心肌炎|脑炎|肾炎|关节炎|白血病|糖尿病|高血压|心脏病|冠心病|中风|脑卒中|癌症|肿瘤)",
    ]

    # Authority level keywords
    AUTHORITY_KEYWORDS = {
        5: ["指南", "标准", "共识", "规范", "国家卫健委", "WHO", "FDA"],
        4: ["专家", "主任", "教授", "权威", "大型研究", "Meta分析", "系统评价"],
        3: ["临床", "试验", "研究", "分析", "数据"],
        2: ["经验", "总结", "报告", "病例"],
        1: ["一般", "通常", "可能", "建议"],
    }

    def __init__(self, llm=None):
        """Initialize the metadata enricher.

        Args:
            llm: Optional LLM for intelligent metadata extraction.
        """
        self.llm = llm

    def transform(
        self, chunks: List[Chunk], trace: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Enrich chunks with medical metadata.

        Args:
            chunks: List of chunks to enrich.
            trace: Optional trace context.

        Returns:
            List of enriched chunks.
        """
        enriched_chunks = []

        for chunk in chunks:
            disease_tags = self._extract_disease_tags(chunk.text)
            authority_level = self._calculate_authority_level(chunk.text, chunk.metadata)
            medical_keywords = self._extract_medical_keywords(chunk.text)

            enriched_chunk = Chunk(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                metadata={
                    **chunk.metadata,
                    "disease_tags": disease_tags,
                    "authority_level": authority_level,
                    "medical_keywords": medical_keywords,
                    "enriched": True,
                },
                source_ref=chunk.source_ref,
                chunk_index=chunk.chunk_index,
            )
            enriched_chunks.append(enriched_chunk)

        self._update_trace(trace, "metadata_enrich", f"enriched {len(chunks)} chunks")
        return enriched_chunks

    def _extract_disease_tags(self, text: str) -> List[str]:
        """Extract disease tags from text.

        Args:
            text: Chunk text.

        Returns:
            List of disease tags.
        """
        tags: Set[str] = set()

        for pattern in self.DISEASE_PATTERNS:
            matches = re.findall(pattern, text)
            tags.update(matches)

        return list(tags)[:10]  # Limit to 10 tags

    def _calculate_authority_level(self, text: str, metadata: Dict[str, Any]) -> int:
        """Calculate authority level (1-5) based on content.

        Args:
            text: Chunk text.
            metadata: Existing metadata.

        Returns:
            Authority level (1-5).
        """
        # Check metadata first
        if "authority_level" in metadata:
            return metadata["authority_level"]

        # Check for authority keywords
        max_level = 1
        for level, keywords in self.AUTHORITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    max_level = max(max_level, level)

        return max_level

    def _extract_medical_keywords(self, text: str) -> List[str]:
        """Extract medical keywords from text.

        Args:
            text: Chunk text.

        Returns:
            List of medical keywords.
        """
        medical_terms = [
            "症状", "诊断", "治疗", "预防", "病因", "病理",
            "检查", "检验", "影像", "超声", "CT", "MRI",
            "药物", "手术", "康复", "预后", "并发症",
        ]

        found = []
        for term in medical_terms:
            if term in text:
                found.append(term)

        return found[:5]  # Limit to 5 keywords
