"""Prescription refusal for medical safety."""

import re
from typing import Optional


class PrescriptionRefusal:
    """Refuses out-of-scope medical requests.

    Safety component that intercepts requests for:
    - Prescription/diagnosis without proper consultation
    - Specific medication recommendations
    - Self-medication advice
    """

    # Patterns that indicate prescription requests
    PRESCRIPTION_PATTERNS = [
        r"开药",
        r"给我开",
        r"吃什么药",
        r"买什么药",
        r"推荐什么药",
        r"药物.*推荐",
        r"药方",
        r"处方",
    ]

    # Patterns that indicate diagnosis requests
    DIAGNOSIS_PATTERNS = [
        r"是什么病",
        r"诊断",
        r"确诊",
        r"是不是.*癌",
        r"是不是.*肿瘤",
        r"是不是.*炎",
        r"得了.*什么病",
    ]

    # Patterns for specific medication requests
    SPECIFIC_MED_PATTERNS = [
        r"吃.*头孢",
        r"吃.*青霉素",
        r"吃.*阿司匹林",
        r"吃.*布洛芬",
        r"用.*激素",
        r"打.*胰岛素",
    ]

    # Disclaimer text
    DISCLAIMER = (
        "【重要提醒】\n\n"
        "作为 AI 医疗导诊系统，我不能为您提供：\n"
        "• 开药或处方\n"
        "• 疾病诊断\n"
        "• 用药建议\n\n"
        "这些行为需要您到正规医疗机构就诊，由持牌医生进行。\n"
        "我可以帮助您：\n"
        "• 描述症状以便更好地分诊\n"
        "• 查找适合的科室\n"
        "• 预约挂号\n\n"
        "如有不适，请立即就医。"
    )

    def should_refuse(self, user_input: str) -> bool:
        """Check if the request should be refused.

        Args:
            user_input: User's input text.

        Returns:
            True if request should be refused.
        """
        if not user_input:
            return False

        text = user_input.strip()

        # Check prescription patterns
        for pattern in self.PRESCRIPTION_PATTERNS:
            if re.search(pattern, text):
                return True

        # Check diagnosis patterns
        for pattern in self.DIAGNOSIS_PATTERNS:
            if re.search(pattern, text):
                return True

        # Check specific medication patterns
        for pattern in self.SPECIFIC_MED_PATTERNS:
            if re.search(pattern, text):
                return True

        return False

    def get_refusal_response(self, reason: Optional[str] = None) -> str:
        """Get refusal response with disclaimer.

        Args:
            reason: Optional specific reason for refusal.

        Returns:
            Refusal message with disclaimer.
        """
        if reason:
            return f"【无法处理】{reason}\n\n{self.DISCLAIMER}"
        return self.DISCLAIMER

    def get_safe_response(self, user_input: str) -> Optional[str]:
        """Get safe alternative response.

        Args:
            user_input: Original user input.

        Returns:
            Safe alternative response, or None if not refusable.
        """
        if not self.should_refuse(user_input):
            return None

        text = user_input.strip().lower()

        # Provide symptom-focused safe alternative
        if any(re.search(p, text) for p in self.PRESCRIPTION_PATTERNS):
            return (
                "我理解您想了解用药信息。但用药需要医生根据您的具体情况来决定。\n\n"
                "建议您：\n"
                "1. 描述您的具体症状\n"
                "2. 我可以帮您分析是否需要就诊\n"
                "3. 推荐合适的科室\n\n"
                "请问您现在有什么不舒服的症状？"
            )

        if any(re.search(p, text) for p in self.DIAGNOSIS_PATTERNS):
            return (
                "我理解您担心自己的健康状况。但疾病诊断需要医生面诊和检查才能确定。\n\n"
                "建议您：\n"
                "1. 详细描述您的症状\n"
                "2. 告诉我症状持续了多久\n"
                "3. 我可以帮您判断是否需要紧急就诊\n\n"
                "请问您有什么不舒服？"
            )

        return self.DISCLAIMER
