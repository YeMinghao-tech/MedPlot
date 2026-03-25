"""Entity extractor for medical conversation analysis."""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExtractedEntities:
    """Container for extracted medical entities."""

    chief_complaint: Optional[str] = None  # 主诉
    symptoms: List[str] = field(default_factory=list)  # 症状列表
    symptom_duration: Optional[str] = None  # 症状持续时间
    severity: Optional[str] = None  # 严重程度
    location: Optional[str] = None  # 疼痛部位
    triggers: List[str] = field(default_factory=list)  # 诱因
    relievers: List[str] = field(default_factory=list)  # 缓解因素
    past_conditions: List[str] = field(default_factory=list)  # 既往病史
    medications: List[str] = field(default_factory=list)  # 用药情况
    allergies: List[str] = field(default_factory=list)  # 过敏史
    family_history: List[str] = field(default_factory=list)  # 家族史
    vital_signs: Dict[str, Any] = field(default_factory=dict)  # 生命体征

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chief_complaint": self.chief_complaint,
            "symptoms": self.symptoms,
            "symptom_duration": self.symptom_duration,
            "severity": self.severity,
            "location": self.location,
            "triggers": self.triggers,
            "relievers": self.relievers,
            "past_conditions": self.past_conditions,
            "medications": self.medications,
            "allergies": self.allergies,
            "family_history": self.family_history,
            "vital_signs": self.vital_signs,
        }


class EntityExtractor:
    """Extracts medical entities from patient conversation.

    Uses pattern matching and keyword detection to identify:
    - Chief complaint (主诉)
    - Symptoms (症状)
    - Duration, severity, location
    - Past medical history
    - Medications and allergies
    """

    # Symptom keywords
    SYMPTOM_PATTERNS = [
        r"发烧|发热|高烧|低烧",
        r"咳嗽|干咳|有痰咳嗽",
        r"头痛|头晕|眩晕",
        r"胸痛|胸闷|心悸",
        r"腹痛|胃痛|肚子疼|腹泻|便秘|呕吐|恶心",
        r"呼吸困难|气短|喘不上气",
        r"乏力|疲劳|没精神|没力气",
        r"水肿|浮肿",
        r"皮疹|瘙痒|皮肤异常",
        r"尿频|尿急|尿痛",
    ]

    # Duration patterns
    DURATION_PATTERNS = [
        (r"持续(\d+)天", lambda m: f"{m.group(1)}天"),
        (r"持续(\d+)周", lambda m: f"{m.group(1)}周"),
        (r"持续(\d+)个月", lambda m: f"{m.group(1)}个月"),
        (r"持续(\d+)年", lambda m: f"{m.group(1)}年"),
        (r"从(.+?)开始", lambda m: m.group(1)),
        (r"已经(.+?)了", lambda m: m.group(1)),
    ]

    # Severity levels
    SEVERITY_KEYWORDS = {
        "轻微": ["轻微", "轻度", "一点点", "不太严重"],
        "中等": ["中等", "明显", "比较严重"],
        "严重": ["严重", "非常严重", "剧烈", "剧痛", "无法忍受"],
    }

    # Location patterns
    LOCATION_PATTERNS = [
        r"头部|头皮|额头|太阳穴",
        r"胸部|胸口|心脏|后背",
        r"腹部|肚子|胃部|左下腹|右下腹",
        r"四肢|手脚|手臂|腿|关节",
        r"腰部|后背|脊椎",
    ]

    # Allergy keywords
    ALLERGY_PATTERNS = [
        r"对(.+?)过敏",
        r"(.+?)过敏",
        r"不能用(.+?)",
        r"吃了(.+?)起疹子",
    ]

    # Medication patterns
    MEDICATION_PATTERNS = [
        r"正在服用(.+?)(?:，|。|$)",
        r"在吃(.+?)(?:，|。|$)",
        r"吃了(.+?)(?:，|。|$)",
        r"服用(.+?)(?:，|。|$)",
        r"使用(.+?)(?:，|。|$)",
    ]

    def __init__(self):
        """Initialize the entity extractor."""
        self._symptom_re = self._compile_patterns(self.SYMPTOM_PATTERNS)
        self._location_re = self._compile_patterns(self.LOCATION_PATTERNS)

    def _compile_patterns(self, patterns: List[str]):
        """Compile patterns into a single regex."""
        return re.compile("|".join(patterns))

    def extract(self, conversation: str) -> ExtractedEntities:
        """Extract medical entities from conversation text.

        Args:
            conversation: The conversation text (can be multi-turn).

        Returns:
            ExtractedEntities with all identified entities.
        """
        entities = ExtractedEntities()

        # Extract chief complaint (usually first sentence describing the issue)
        entities.chief_complaint = self._extract_chief_complaint(conversation)

        # Extract symptoms
        entities.symptoms = self._extract_symptoms(conversation)

        # Extract duration
        entities.symptom_duration = self._extract_duration(conversation)

        # Extract severity
        entities.severity = self._extract_severity(conversation)

        # Extract location
        entities.location = self._extract_location(conversation)

        # Extract allergies
        entities.allergies = self._extract_allergies(conversation)

        # Extract medications
        entities.medications = self._extract_medications(conversation)

        # Extract past conditions
        entities.past_conditions = self._extract_past_conditions(conversation)

        return entities

    def _extract_chief_complaint(self, text: str) -> Optional[str]:
        """Extract the chief complaint (主诉)."""
        # Look for patterns like "主要症状是..." or "不舒服..."
        patterns = [
            r"(?:主要|来看|因为).*?(?:症状|问题|不舒服)(?:是|：|:)(.+?)[。.]",
            r"(.+?)已经(.+?)了",  # e.g., "头痛已经3天了"
            r"(?:我|病人)(?:觉得|感觉|有)(.+?)(?:已经|持续|好几)",  # "我感觉头痛已经..."
        ]

        for pattern in patterns:
            m = re.search(pattern, text)
            if m:
                return m.group(1).strip()

        # Fallback: first sentence containing symptom keywords
        sentences = text.split("。")
        for s in sentences:
            if any(re.search(p, s) for p in self.SYMPTOM_PATTERNS):
                return s.strip()

        return None

    def _extract_symptoms(self, text: str) -> List[str]:
        """Extract symptom keywords."""
        symptoms = []
        matches = self._symptom_re.findall(text)
        # Remove duplicates while preserving order
        seen = set()
        for s in matches:
            if s not in seen:
                seen.add(s)
                symptoms.append(s)
        return symptoms

    def _extract_duration(self, text: str) -> Optional[str]:
        """Extract symptom duration."""
        for pattern, handler in self.DURATION_PATTERNS:
            m = re.search(pattern, text)
            if m:
                try:
                    return handler(m)
                except Exception:
                    return m.group(0)
        return None

    def _extract_severity(self, text: str) -> Optional[str]:
        """Extract severity level."""
        for severity, keywords in self.SEVERITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return severity
        return None

    def _extract_location(self, text: str) -> Optional[str]:
        """Extract pain/f discomfort location."""
        matches = self._location_re.findall(text)
        if matches:
            return "、".join(matches[:3])  # Limit to 3 locations
        return None

    def _extract_allergies(self, text: str) -> List[str]:
        """Extract allergy information."""
        allergies = []
        for pattern in self.ALLERGY_PATTERNS:
            matches = re.findall(pattern, text)
            for m in matches:
                # Clean up and validate
                allergy = m.strip().rstrip("过敏")
                if allergy and len(allergy) > 1:
                    allergies.append(allergy)
        return list(set(allergies))  # Remove duplicates

    def _extract_medications(self, text: str) -> List[str]:
        """Extract current medications."""
        medications = []
        for pattern in self.MEDICATION_PATTERNS:
            matches = re.findall(pattern, text)
            for m in matches:
                med = m.strip()
                if med and len(med) > 1:
                    medications.append(med)
        return list(set(medications))

    def _extract_past_conditions(self, text: str) -> List[str]:
        """Extract past medical conditions."""
        conditions = []
        past_keywords = ["以前有", "之前有", "患过", "得过", "有(.+?)病史"]

        for keyword in past_keywords:
            if keyword.startswith("有"):
                pattern = keyword.replace("(.+?)", r"(.+?)")
                matches = re.findall(pattern, text)
                conditions.extend([m.strip() for m in matches if m.strip()])
            elif keyword in text:
                # Find what follows the keyword
                idx = text.find(keyword)
                remaining = text[idx + len(keyword):]
                m = re.match(r"(.+?)[,，。.]", remaining)
                if m:
                    conditions.append(m.group(1).strip())

        return list(set(conditions))
