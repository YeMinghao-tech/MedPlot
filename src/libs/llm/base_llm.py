"""Base LLM interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseLLM(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """Generate a chat response.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys.
                     Example: [{"role": "user", "content": "Hello!"}]
            **kwargs: Additional provider-specific parameters.

        Returns:
            The generated response text.
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model name."""
        pass
