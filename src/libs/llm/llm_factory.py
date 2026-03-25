"""LLM Factory for creating LLM instances based on configuration."""

from typing import Optional

from src.core.settings import Settings
from src.libs.llm.base_llm import BaseLLM
from src.libs.llm.base_vision_llm import BaseVisionLLM
from src.libs.llm.ollama_llm import OllamaLLM
from src.libs.llm.openai_llm import OpenAILLM
from src.libs.llm.qwen_llm import QwenLLM
from src.libs.llm.qwen_vl_llm import QwenVLLM


class LLMFactory:
    """Factory for creating LLM instances based on configuration."""

    _providers = {
        "dashscope": QwenLLM,
        "openai": OpenAILLM,
        "ollama": OllamaLLM,
    }

    _vision_providers = {
        "dashscope": QwenVLLM,
    }

    @classmethod
    def create(cls, settings: Settings) -> BaseLLM:
        """Create an LLM instance based on settings.

        Args:
            settings: Settings object containing LLM configuration.

        Returns:
            An instance of a BaseLLM subclass.

        Raises:
            ValueError: If the provider is not supported.
        """
        provider = settings.llm.provider.lower()
        model = settings.llm.model
        api_key = settings.llm.api_key

        if provider not in cls._providers:
            raise ValueError(
                f"Unsupported LLM provider: {provider}. "
                f"Supported providers: {list(cls._providers.keys())}"
            )

        llm_class = cls._providers[provider]

        # Pass provider-specific kwargs
        if provider == "ollama":
            return llm_class(model=model)
        else:
            return llm_class(model=model, api_key=api_key)

    @classmethod
    def register_provider(cls, name: str, llm_class: type) -> None:
        """Register a new LLM provider.

        Args:
            name: Provider name (e.g., 'openai', 'ollama').
            llm_class: The LLM class to register.
        """
        cls._providers[name.lower()] = llm_class

    @classmethod
    def create_vision_llm(cls, settings: Settings) -> BaseVisionLLM:
        """Create a Vision LLM instance based on settings.

        Args:
            settings: Settings object containing Vision LLM configuration.

        Returns:
            An instance of a BaseVisionLLM subclass.

        Raises:
            ValueError: If the provider is not supported.
        """
        provider = settings.vision_llm.provider.lower()
        model = settings.vision_llm.model
        api_key = settings.llm.api_key  # Vision LLM uses same API key

        if provider not in cls._vision_providers:
            raise ValueError(
                f"Unsupported Vision LLM provider: {provider}. "
                f"Supported providers: {list(cls._vision_providers.keys())}"
            )

        vl_class = cls._vision_providers[provider]
        return vl_class(model=model, api_key=api_key)

    @classmethod
    def register_vision_provider(cls, name: str, vl_class: type) -> None:
        """Register a new Vision LLM provider.

        Args:
            name: Provider name (e.g., 'dashscope').
            vl_class: The Vision LLM class to register.
        """
        cls._vision_providers[name.lower()] = vl_class
