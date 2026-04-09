"""Qwen LLM implementation using DashScope."""

import logging
from typing import Any, Dict, List, Optional, Tuple, Type

from src.libs.llm.base_llm import BaseLLM

logger = logging.getLogger(__name__)

# Exceptions that should trigger a retry
RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    TimeoutError,
    ConnectionError,
    OSError,
)


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
        """Generate a chat response using Qwen with retry on failure.

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

        # Retry logic with exponential backoff
        max_retries = 3
        initial_delay = 2.0
        backoff_factor = 2.0

        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                # Convert messages to DashScope format
                dashscope_messages = self._convert_messages(messages)

                # Set API key if available
                if self.api_key:
                    import os

                    os.environ["DASHSCOPE_API_KEY"] = self.api_key
                    dashscope.api_key = self.api_key

                response = dashscope.Generation.call(
                    model=self.model,
                    messages=dashscope_messages,
                    result_format="message",
                    request_timeout=30,
                    **kwargs,
                )

                if response.status_code != 200:
                    # Check if error is retryable (5xx errors)
                    if response.code and str(response.code).startswith('5'):
                        raise RuntimeError(
                            f"DashScope API error: {response.code} - {response.message}"
                        )
                    # Non-retryable error (4xx)
                    raise RuntimeError(
                        f"DashScope API error: {response.code} - {response.message}"
                    )

                return response.output.choices[0].message.content

            except RETRYABLE_EXCEPTIONS as e:
                last_exception = e
                if attempt < max_retries:
                    delay = min(initial_delay * (backoff_factor ** attempt), 30.0)
                    logger.warning(
                        f"LLM attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    import time
                    time.sleep(delay)
                else:
                    logger.error(f"All {max_retries + 1} LLM attempts failed")
                    raise

        if last_exception:
            raise last_exception
        raise RuntimeError("LLM call failed after retries")

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
