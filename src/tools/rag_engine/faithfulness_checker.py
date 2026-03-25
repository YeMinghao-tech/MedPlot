"""Faithfulness checker for hallucination defense.

Verifies that generated medical records are faithful to source materials.
"""

from typing import List, Optional, Set
import re


class FaithfulnessChecker:
    """Checks faithfulness of generated content against source materials.

    Used in H5 to prevent hallucination in generated medical records.
    Compares generated content against retrieved context chunks.
    """

    # Patterns that indicate potentially hallucinated claims
    HALLUCINATION_PATTERNS = [
        r"根据.*研究显示",
        r"数据显示",
        r"医学界公认",
        r"通常.*会.*癌",
        r"一定是.*癌",
        r"肯定是.*晚期",
        r"必须.*手术",
        r"只能.*治疗",
    ]

    # Specific medical terms that should not be invented
    invented_symptoms = ["幻觉症状", "虚假疼痛", "伪造反应"]

    def __init__(self, min_faithfulness_score: float = 0.8):
        """Initialize the faithfulness checker.

        Args:
            min_faithfulness_score: Minimum score to pass (0.0 - 1.0).
        """
        self.min_faithfulness_score = min_faithfulness_score

    def check(
        self,
        generated_record: str,
        source_chunks: List[str],
    ) -> tuple[bool, float, List[str]]:
        """Check if generated record is faithful to source chunks.

        Args:
            generated_record: The generated medical record text.
            source_chunks: List of source context chunks.

        Returns:
            Tuple of (is_faithful, score, warnings).
            is_faithful: True if record passes faithfulness check.
            score: Faithfulness score (0.0 - 1.0).
            warnings: List of warning messages.
        """
        if not generated_record or not source_chunks:
            return True, 1.0, []

        warnings = []
        score = 1.0

        # Combine source chunks for comparison
        source_text = " ".join(source_chunks).lower()

        # Check for invented medical terms
        invented_found = self._check_invented_terms(generated_record)
        if invented_found:
            warnings.append(f"发现疑似虚构内容: {invented_found}")
            score -= 0.5

        # Check for unsupported specific claims
        unsupported_claims = self._check_unsupported_claims(generated_record, source_text)
        if unsupported_claims:
            warnings.append(f"发现无来源支持的具体声明: {unsupported_claims}")
            score -= 0.2 * len(unsupported_claims)

        # Check entity consistency
        entity_warnings = self._check_entity_consistency(generated_record, source_chunks)
        warnings.extend(entity_warnings)
        if entity_warnings:
            score -= 0.1 * len(entity_warnings)

        # Ensure score is bounded
        score = max(0.0, min(1.0, score))

        is_faithful = score >= self.min_faithfulness_score

        return is_faithful, score, warnings

    def _check_invented_terms(self, text: str) -> List[str]:
        """Check for invented/non-existent medical terms."""
        found = []
        for term in self.invented_symptoms:
            if term in text:
                found.append(term)
        return found

    def _check_unsupported_claims(self, text: str, source: str) -> List[str]:
        """Check for claims that are too specific without source support."""
        unsupported = []
        text_lower = text.lower()

        for pattern in self.HALLUCINATION_PATTERNS:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                claim = match.group()
                # Check if claim is actually supported by source
                if claim.lower() not in source:
                    unsupported.append(claim)

        return unsupported[:5]  # Limit to first 5

    def _check_entity_consistency(
        self,
        text: str,
        source_chunks: List[str],
    ) -> List[str]:
        """Check for entity consistency with source.

        Extracts key entities from generated text and verifies
        they appear in source chunks.
        """
        warnings = []

        # Extract potential symptom mentions from generated text
        symptom_pattern = r"(症状|表现为?|表现为)([^，。,]+)"
        generated_symptoms = re.findall(symptom_pattern, text)

        for _, symptom in generated_symptoms:
            symptom = symptom.strip().lower()
            # Check if symptom appears in any source chunk
            found = any(symptom in chunk.lower() for chunk in source_chunks)
            if not found and len(symptom) > 2:
                warnings.append(f"症状'{symptom}'未在来源中找到支持")

        return warnings[:3]  # Limit warnings

    def get_safe_response(
        self,
        is_faithful: bool,
        score: float,
        warnings: List[str],
    ) -> Optional[str]:
        """Get safe response when faithfulness check fails.

        Args:
            is_faithful: Whether the content passed the check.
            score: Faithfulness score.
            warnings: List of warnings.

        Returns:
            Safe alternative response or None if check passed.
        """
        if is_faithful:
            return None

        warning_text = "\n".join(f"- {w}" for w in warnings[:3])

        return (
            "【医疗安全提示】\n\n"
            "我在整理您的病历信息时发现内容可能存在不一致，"
            "为了确保信息准确性，建议您：\n\n"
            "1. 核对以下信息：\n"
            f"{warning_text}\n\n"
            "2. 如有疑问，请咨询医生\n"
            "3. 不要仅凭AI生成的病历进行自我诊断\n\n"
            "您的健康安全是第一位的。"
        )
