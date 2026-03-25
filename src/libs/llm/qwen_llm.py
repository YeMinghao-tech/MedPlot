"""Qwen LLM implementation using DashScope."""

from typing import Any, Dict, List, Optional

from src.libs.llm.base_llm import BaseLLM


class QwenLLM(BaseLLM):
    """Qwen LLM implementation using DashScope API."""

    def __init__(self, model: str = "qwen-max", api_key: Optional[str] = None):
        """Initialize Qwen LLM.

        Args:
            model: Model name (default: qwen-max).
            api_key: DashScope API key. If None, will try to get from environment.
        """
        self.model = model
        self.api_key = api_key or self._get_api_key()

    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment."""
        import os

        return os.environ.get("DASHSCOPE_API_KEY")

    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """Generate a chat response using Qwen.

        Args:
            messages: List of message dictionaries.
            **kwargs: Additional parameters (temperature, top_p, etc.)

        Returns:
            The generated response text.
        """
        try:
            import dashscope
        except ImportError:
            raise ImportError(
                "dashscope package is required for Qwen LLM. "
                "Install it with: pip install dashscope"
            )

        # Convert messages to DashScope format
        dashscope_messages = self._convert_messages(messages)

        # Set API key if available
        if self.api_key:
            import os

            os.environ["DASHSCOPE_API_KEY"] = self.api_key

        response = dashscope.Generation.call(
            model=self.model,
            messages=dashscope_messages,
            result_format="message",
            **kwargs,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"DashScope API error: {response.code} - {response.message}"
            )

        return response.output.choices[0].message.content

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict]:
        """Convert messages to DashScope format."""
        converted = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                role = "system"
            elif role == "assistant":
                role = "assistant"
            else:
                role = "user"
            converted.append({"role": role, "content": msg.get("content", "")})
        return converted

    def get_model_name(self) -> str:
        """Return the model name."""
        return self.model
