"""OpenAI LLM implementation."""

from typing import Any, Dict, List, Optional

from src.libs.llm.base_llm import BaseLLM


class OpenAILLM(BaseLLM):
    """OpenAI LLM implementation."""

    def __init__(
        self,
        model: str = "gpt-4",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize OpenAI LLM.

        Args:
            model: Model name (default: gpt-4).
            api_key: OpenAI API key. If None, will try to get from environment.
            base_url: Optional base URL for OpenAI-compatible APIs.
        """
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """Generate a chat response using OpenAI.

        Args:
            messages: List of message dictionaries.
            **kwargs: Additional parameters (temperature, top_p, etc.)

        Returns:
            The generated response text.
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package is required for OpenAI LLM. "
                "Install it with: pip install openai"
            )

        client_kwargs = {"api_key": self.api_key} if self.api_key else {}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        client = OpenAI(**client_kwargs)

        # Convert messages to OpenAI format
        openai_messages = self._convert_messages(messages)

        response = client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            **kwargs,
        )

        return response.choices[0].message.content

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict]:
        """Convert messages to OpenAI format."""
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
