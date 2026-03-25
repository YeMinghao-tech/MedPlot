"""Query processor for medical RAG with colloquial to medical term mapping."""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProcessedQuery:
    """Processed query with transformations applied."""

    original: str
    expanded_terms: List[str] = field(default_factory=list)
    medical_terms: Dict[str, str] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)


class QueryProcessor:
    """Processes user queries for medical RAG.

    Handles:
    - Colloquial to medical term mapping
    - Symptom normalization
    - Query expansion
    - Filter extraction
    """

    # Common colloquial to medical term mappings
    COLLOQUIAL_MAP: Dict[str, str] = {
        # General symptoms
        "发烧": "发热",
        "高烧": "发热",
        "低烧": "发热",
        "肚子疼": "腹痛",
        "胃疼": "腹痛",
        "头疼": "头痛",
        "头昏": "头晕",
        "迷糊": "头晕",
        "流鼻涕": "鼻溢",
        "咳嗽": "咳嗽",
        "拉肚子": "腹泻",
        "拉稀": "腹泻",
        "便秘": "排便困难",
        # Cardiac
        "心慌": "心悸",
        "心跳快": "心动过速",
        "心跳慢": "心动过缓",
        "胸闷": "胸闷",
        "胸口疼": "胸痛",
        "心脏疼": "胸痛",
        # Respiratory
        "气短": "呼吸困难",
        "喘不上气": "呼吸困难",
        "憋气": "呼吸困难",
        # Neurological
        "手脚麻": "感觉异常",
        "手脚麻木": "感觉异常",
        "浑身没劲": "乏力",
        "没精神": "乏力",
        # GI
        "恶心": "恶心",
        "想吐": "呕吐",
        "吃不下": "食欲减退",
        "吃不下饭": "食欲减退",
        # Pain descriptions
        "绞痛": "绞痛",
        "胀痛": "胀痛",
        "刺痛": "刺痛",
        "隐痛": "隐痛",
        "剧痛": "剧痛",
        "钝痛": "钝痛",
    }

    # Medical term synonyms (for expansion)
    SYNONYM_MAP: Dict[str, List[str]] = {
        "发热": ["发烧", "高热", "体温升高"],
        "腹痛": ["肚子痛", "胃痛", "腹部疼痛"],
        "胸痛": ["胸口疼", "心脏疼", "胸部疼痛"],
        "呼吸困难": ["气短", "喘不上气", "憋气", "呼吸急促"],
        "腹泻": ["拉肚子", "拉稀", "水样便"],
        "头痛": ["头疼", "头部疼痛"],
        "眩晕": ["头晕", "头昏", "天旋地转"],
        "乏力": ["疲劳", "没劲", "疲倦"],
        "恶心": ["想吐", "反胃"],
        "食欲减退": ["吃不下", "不想吃饭", "纳差"],
    }

    def __init__(self):
        """Initialize the query processor."""
        pass

    def process(self, query: str) -> ProcessedQuery:
        """Process a user query.

        Args:
            query: Raw user query (often colloquial).

        Returns:
            ProcessedQuery with expanded terms and mappings.
        """
        processed = ProcessedQuery(original=query)

        # Normalize colloquial terms
        normalized = query
        medical_terms = {}

        for colloquial, medical in self.COLLOQUIAL_MAP.items():
            if colloquial in normalized:
                normalized = normalized.replace(colloquial, medical)
                medical_terms[colloquial] = medical
                processed.expanded_terms.append(f"{colloquial}→{medical}")

        # Expand with synonyms
        for medical, synonyms in self.SYNONYM_MAP.items():
            if medical in normalized:
                for syn in synonyms:
                    if syn not in normalized:
                        processed.expanded_terms.append(f"{syn}→{medical}")

        processed.medical_terms = medical_terms

        # Extract filters (e.g., authority level, disease tags)
        filters = self._extract_filters(normalized)
        processed.filters = filters

        return processed

    def _extract_filters(self, query: str) -> Dict[str, Any]:
        """Extract metadata filters from query.

        Args:
            query: Normalized query text.

        Returns:
            Filter dictionary.
        """
        filters = {}

        # Check for authority level hints
        if any(kw in query for kw in ["指南", "标准", "共识"]):
            filters["authority_level"] = {"$gte": 4}
        elif any(kw in query for kw in ["专家", "权威"]):
            filters["authority_level"] = {"$gte": 3}

        return filters

    def expand_query(self, query: str) -> List[str]:
        """Expand a query with synonyms and related terms.

        Args:
            query: Query text.

        Returns:
            List of expanded query strings.
        """
        processed = self.process(query)
        variants = [processed.original]

        # Add normalized version
        normalized = processed.original
        for col, med in processed.medical_terms.items():
            normalized = normalized.replace(col, med)
        if normalized != processed.original:
            variants.append(normalized)

        # Add expanded terms
        for term_list in self.SYNONYM_MAP.values():
            for term in term_list:
                if term in processed.original:
                    variants.append(processed.original)

        return list(set(variants))
