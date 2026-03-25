"""Ollama LLM implementation."""

from typing import Any, Dict, List, Optional

from src.libs.llm.base_llm import BaseLLM


class OllamaLLM(BaseLLM):
    """Ollama LLM implementation for local models."""

    def __init__(
        self,
        model: str = "llama2",
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:11434",
    ):
        """Initialize Ollama LLM.

        Args:
            model: Model name (default: llama2).
            base_url: Base URL for Ollama API (default: http://localhost:11434).
        """
        self.model = model
        self.base_url = base_url.rstrip("/")

    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """Generate a chat response using Ollama.

        Args:
            messages: List of message dictionaries.
            **kwargs: Additional parameters (temperature, top_p, etc.)

        Returns:
            The generated response text.
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx package is required for Ollama LLM. "
                "Install it with: pip install httpx"
            )

        # Convert messages to Ollama format
        ollama_messages = self._convert_messages(messages)

        # Build request payload
        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
        }
        payload.update({k: v for k, v in kwargs.items() if v is not None})

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return data.get("message", {}).get("content", "")

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict]:
        """Convert messages to Ollama format."""
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
