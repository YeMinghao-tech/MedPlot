"""Intent classifier for medical consultation."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.agent.planner.emergency_interceptor import EmergencyInterceptor


class Intent(Enum):
    """Available intents."""

    MEDICAL_CONSULTATION = "medical_consultation"  # 问诊
    APPOINTMENT_BOOKING = "appointment_booking"  # 挂号
    MEDICAL_KNOWLEDGE = "medical_knowledge"  # 科普
    CONFIRM = "confirm"  # 确认
    RED_FLAG = "red_flag"  # 红线拦截
    GREETING = "greeting"  # 问候
    UNKNOWN = "unknown"  # 未知


@dataclass
class IntentResult:
    """Result of intent classification."""

    intent: Intent
    confidence: float  # 0.0 - 1.0
    reasoning: str
    keywords: list = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


class IntentClassifier:
    """Classifies user intent in medical consultation.

    Uses rule-based keyword matching with optional LLM enhancement.
    Priority: RED_FLAG > GREETING > CONFIRM > medical keywords > ...

    Emergency keywords are checked first via EmergencyInterceptor.
    """

    # Emergency keywords (highest priority - checked before classification)
    EMERGENCY_KEYWORDS = [
        "胸痛", "胸闷", "心绞痛", "心脏疼",
        "大出血", "流血不止", "吐血",
        "意识模糊", "意识丧失", "昏迷",
        "呼吸困难", "窒息",
        "中风", "脑卒中", "偏瘫",
        "过敏性休克", "休克",
        "剧烈头痛", "头痛欲裂",
    ]

    # Medical consultation keywords
    CONSULTATION_KEYWORDS = [
        "症状", "不舒服", "感觉", "表现",
        "发烧", "发热", "咳嗽", "疼痛", "痛",
        "肚子", "头部", "胸部", "背部",
        "治疗", "怎么治", "如何治疗", "怎么办",
        "原因", "为什么", "怎么会",
    ]

    # Appointment booking keywords
    APPOINTMENT_KEYWORDS = [
        "挂号", "预约", "看医生", "就诊",
        "预约挂号", "网上挂号",
        "医生", "门诊", "专家",
        "时间", "几点", "哪天",
    ]

    # Medical knowledge (general inquiry) keywords
    KNOWLEDGE_KEYWORDS = [
        "什么是", "请问", "解释",
        "科普", "知识", "常识",
        "疾病", "药物", "药品",
        "检查", "体检",
        "预防", "注意事项",
    ]

    # Confirmation keywords
    CONFIRM_KEYWORDS = [
        "是的", "对", "没错", "正确",
        "明白了", "清楚了", "知道了",
        "好的", "可以", "行",
        "确认", "肯定",
    ]

    # Greeting keywords
    GREETING_KEYWORDS = [
        "你好", "您好", "hi", "hello",
        "早上好", "下午好", "晚上好",
        "在吗", "在不在",
    ]

    def __init__(self, llm_client=None):
        """Initialize the intent classifier.

        Args:
            llm_client: Optional LLM client for ambiguous cases.
        """
        self.llm = llm_client
        self.emergency_interceptor = EmergencyInterceptor()

    def classify(self, user_input: str) -> IntentResult:
        """Classify user intent from input text.

        Args:
            user_input: User's input text.

        Returns:
            IntentResult with classified intent and confidence.
        """
        if not user_input or not user_input.strip():
            return IntentResult(
                intent=Intent.UNKNOWN,
                confidence=0.0,
                reasoning="Empty input",
            )

        text = user_input.strip()
        text_lower = text.lower()

        # Step 1: Check for red flag (emergency) first
        emergency_result = self.emergency_interceptor.intercept(text)
        if emergency_result:
            return IntentResult(
                intent=Intent.RED_FLAG,
                confidence=1.0,
                reasoning=f"Emergency keyword detected: {emergency_result}",
                keywords=[emergency_result],
            )

        # Step 2: Check for greeting
        if self._matches_any(text, self.GREETING_KEYWORDS):
            return IntentResult(
                intent=Intent.GREETING,
                confidence=0.9,
                reasoning="Greeting keyword matched",
                keywords=self._find_matched_keywords(text, self.GREETING_KEYWORDS),
            )

        # Step 3: Check for confirmation
        if self._matches_any(text, self.CONFIRM_KEYWORDS):
            return IntentResult(
                intent=Intent.CONFIRM,
                confidence=0.85,
                reasoning="Confirmation keyword matched",
                keywords=self._find_matched_keywords(text, self.CONFIRM_KEYWORDS),
            )

        # Step 4: Check for appointment booking
        appointment_score = self._count_matches(text, self.APPOINTMENT_KEYWORDS)
        if appointment_score >= 1:
            return IntentResult(
                intent=Intent.APPOINTMENT_BOOKING,
                confidence=min(0.9, 0.5 + appointment_score * 0.2),
                reasoning=f"Appointment keywords matched (score: {appointment_score})",
                keywords=self._find_matched_keywords(text, self.APPOINTMENT_KEYWORDS),
            )

        # Step 5: Check for medical knowledge inquiry
        knowledge_score = self._count_matches(text, self.KNOWLEDGE_KEYWORDS)
        consultation_score = self._count_matches(text, self.CONSULTATION_KEYWORDS)

        if knowledge_score > consultation_score and knowledge_score >= 1:
            return IntentResult(
                intent=Intent.MEDICAL_KNOWLEDGE,
                confidence=min(0.85, 0.4 + knowledge_score * 0.15),
                reasoning=f"Knowledge keywords matched (score: {knowledge_score})",
                keywords=self._find_matched_keywords(text, self.KNOWLEDGE_KEYWORDS),
            )

        # Step 6: Default to medical consultation
        if consultation_score >= 1:
            return IntentResult(
                intent=Intent.MEDICAL_CONSULTATION,
                confidence=min(0.85, 0.4 + consultation_score * 0.15),
                reasoning=f"Consultation keywords matched (score: {consultation_score})",
                keywords=self._find_matched_keywords(text, self.CONSULTATION_KEYWORDS),
            )

        # Step 7: LLM fallback for ambiguous cases
        if self.llm:
            return self._classify_with_llm(text)
        else:
            return IntentResult(
                intent=Intent.UNKNOWN,
                confidence=0.5,
                reasoning="No keywords matched and no LLM available",
            )

    def _matches_any(self, text: str, keywords: list) -> bool:
        """Check if text contains any of the keywords."""
        for kw in keywords:
            if kw in text:
                return True
        return False

    def _count_matches(self, text: str, keywords: list) -> int:
        """Count how many keywords are in the text."""
        count = 0
        for kw in keywords:
            if kw in text:
                count += 1
        return count

    def _find_matched_keywords(self, text: str, keywords: list) -> list:
        """Find all matched keywords."""
        return [kw for kw in keywords if kw in text]

    def _classify_with_llm(self, text: str) -> IntentResult:
        """Use LLM for ambiguous classification."""
        # TODO: Implement LLM-based classification
        return IntentResult(
            intent=Intent.UNKNOWN,
            confidence=0.5,
            reasoning="LLM classification not yet implemented",
        )
