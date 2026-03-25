"""Emergency interceptor for red flag symptoms."""

from typing import Optional


class EmergencyInterceptor:
    """Intercepts emergency/red flag symptoms and provides immediate guidance.

    This is a critical safety component that runs before any other processing.
    """

    # Red flag symptoms that require immediate medical attention
    RED_FLAG_PATTERNS = {
        "胸痛": "【紧急】胸痛可能提示心脏问题，请立即就医或拨打120！",
        "胸闷": "【紧急】胸闷可能提示心脏问题，请立即就医或拨打120！",
        "大出血": "【紧急】出现大出血，请立即就医或拨打120！",
        "意识模糊": "【紧急】意识模糊或昏迷，请立即就医或拨打120！",
        "呼吸困难": "【紧急】呼吸困难为急症，请立即就医或拨打120！",
        "中风": "【紧急】中风症状，请立即就医或拨打120！",
        "休克": "【紧急】休克状态，请立即就医或拨打120！",
    }

    # Patterns that indicate potential emergency (partial match)
    EMERGENCY_PARTIALS = [
        "胸痛", "胸闷", "心绞痛", "心脏疼",
        "大出血", "吐血", "流血不止",
        "意识模糊", "意识丧失", "昏迷", "不省人事",
        "呼吸困难", "气短严重", "窒息",
        "偏瘫", "口眼歪斜", "脑卒中",
        "剧烈头痛", "头痛欲裂",
        "过敏性休克",
    ]

    def intercept(self, user_input: str) -> Optional[str]:
        """Check if input contains emergency keywords.

        Args:
            user_input: User's input text.

        Returns:
            Emergency keyword if found, None otherwise.
        """
        if not user_input:
            return None

        text = user_input.strip()

        # Check exact matches first
        for keyword in self.RED_FLAG_PATTERNS:
            if keyword in text:
                return keyword

        # Check partial matches
        for partial in self.EMERGENCY_PARTIALS:
            if partial in text:
                return partial

        return None

    def get_emergency_response(self, keyword: str) -> str:
        """Get emergency guidance message.

        Args:
            keyword: Detected emergency keyword.

        Returns:
            Emergency guidance message.
        """
        return self.RED_FLAG_PATTERNS.get(
            keyword,
            "【紧急】检测到可能的危急症状，请立即就医或拨打120！"
        )
