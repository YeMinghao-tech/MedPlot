"""Base Vision LLM interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Union


class BaseVisionLLM(ABC):
    """Abstract base class for Vision LLM providers."""

    @abstractmethod
    def chat_with_image(
        self, text: str, image: Union[str, bytes], **kwargs
    ) -> str:
        """Generate a response based on text and image.

        Args:
            text: The text prompt.
            image: Image file path or bytes.
            **kwargs: Additional provider-specific parameters.

        Returns:
            The generated response text.
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model name."""
        pass
