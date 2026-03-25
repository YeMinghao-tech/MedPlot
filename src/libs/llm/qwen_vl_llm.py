"""Qwen VL LLM implementation using DashScope."""

from typing import Any, Dict, Union

from src.libs.llm.base_vision_llm import BaseVisionLLM


class QwenVLLM(BaseVisionLLM):
    """Qwen Vision LLM implementation using DashScope API."""

    def __init__(self, model: str = "qwen-vl-max", api_key: str = None):
        """Initialize Qwen VL LLM.

        Args:
            model: Model name (default: qwen-vl-max).
            api_key: DashScope API key. If None, will try to get from environment.
        """
        self.model = model
        self.api_key = api_key or self._get_api_key()

    def _get_api_key(self) -> str:
        """Get API key from environment."""
        import os

        return os.environ.get("DASHSCOPE_API_KEY", "")

    def chat_with_image(
        self, text: str, image: Union[str, bytes], **kwargs
    ) -> str:
        """Generate a response based on text and image.

        Args:
            text: The text prompt.
            image: Image file path or bytes.
            **kwargs: Additional parameters.

        Returns:
            The generated response text.
        """
        try:
            import dashscope
            from dashscope import MultiModalConversation
        except ImportError:
            raise ImportError(
                "dashscope package is required for Qwen VL LLM. "
                "Install it with: pip install dashscope"
            )

        if self.api_key:
            import os

            os.environ["DASHSCOPE_API_KEY"] = self.api_key

        # Handle image input
        if isinstance(image, str):
            # File path
            image_input = {"image": image}
        else:
            # Already bytes or need to handle differently
            image_input = {"image": image}

        messages = [
            {
                "role": "user",
                "content": [
                    {"image": image if isinstance(image, str) else ""},
                    {"text": text},
                ],
            }
        ]

        # If image is bytes, we need to provide URL or base64
        if isinstance(image, bytes):
            import base64

            image_data = base64.b64encode(image).decode("utf-8")
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": f"data:image/jpeg;base64,{image_data}"},
                        {"text": text},
                    ],
                }
            ]

        response = MultiModalConversation.call(
            model=self.model,
            messages=messages,
            **kwargs,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"DashScope Vision API error: {response.code} - {response.message}"
            )

        return response.output.choices[0].message.content

    def get_model_name(self) -> str:
        """Return the model name."""
        return self.model
