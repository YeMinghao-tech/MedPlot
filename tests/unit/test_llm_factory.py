"""Tests for LLM Factory."""

from unittest.mock import MagicMock, patch

import pytest

from src.core.settings import Settings
from src.libs.llm.base_llm import BaseLLM
from src.libs.llm.llm_factory import LLMFactory
from src.libs.llm.ollama_llm import OllamaLLM
from src.libs.llm.openai_llm import OpenAILLM
from src.libs.llm.qwen_llm import QwenLLM


class FakeLLM(BaseLLM):
    """Fake LLM implementation for testing."""

    def __init__(self, model: str = "fake-model", api_key: str = None):
        self.model = model
        self.api_key = api_key

    def chat(self, messages, **kwargs) -> str:
        return "fake response"

    def get_model_name(self) -> str:
        return self.model


class TestLLMFactory:
    """Test LLMFactory.create method."""

    def test_create_qwen_llm(self):
        """Test creating a Qwen LLM."""
        settings = Settings()
        settings.llm.provider = "dashscope"
        settings.llm.model = "qwen-max"
        settings.llm.api_key = "test-key"

        llm = LLMFactory.create(settings)
        assert isinstance(llm, QwenLLM)
        assert llm.model == "qwen-max"
        assert llm.api_key == "test-key"

    def test_create_openai_llm(self):
        """Test creating an OpenAI LLM."""
        settings = Settings()
        settings.llm.provider = "openai"
        settings.llm.model = "gpt-4"
        settings.llm.api_key = "test-key"

        llm = LLMFactory.create(settings)
        assert isinstance(llm, OpenAILLM)
        assert llm.model == "gpt-4"

    def test_create_ollama_llm(self):
        """Test creating an Ollama LLM."""
        settings = Settings()
        settings.llm.provider = "ollama"
        settings.llm.model = "llama2"

        llm = LLMFactory.create(settings)
        assert isinstance(llm, OllamaLLM)
        assert llm.model == "llama2"

    def test_create_unsupported_provider_raises_error(self):
        """Test that unsupported provider raises ValueError."""
        settings = Settings()
        settings.llm.provider = "unsupported"
        settings.llm.model = "some-model"

        with pytest.raises(ValueError) as exc_info:
            LLMFactory.create(settings)
        assert "Unsupported LLM provider" in str(exc_info.value)
        assert "unsupported" in str(exc_info.value)

    def test_provider_case_insensitive(self):
        """Test that provider names are case-insensitive."""
        settings = Settings()
        settings.llm.provider = "DASHSCOPE"
        settings.llm.model = "qwen-max"

        llm = LLMFactory.create(settings)
        assert isinstance(llm, QwenLLM)

    def test_register_provider(self):
        """Test registering a new provider."""
        LLMFactory.register_provider("fake", FakeLLM)

        settings = Settings()
        settings.llm.provider = "fake"
        settings.llm.model = "fake-model"

        llm = LLMFactory.create(settings)
        assert isinstance(llm, FakeLLM)


class TestBaseLLMInterface:
    """Test that LLM implementations conform to BaseLLM interface."""

    def test_qwen_llm_has_chat_method(self):
        """Test QwenLLM has chat method."""
        llm = QwenLLM(model="qwen-max")
        assert hasattr(llm, "chat")
        assert callable(llm.chat)

    def test_qwen_llm_has_get_model_name(self):
        """Test QwenLLM has get_model_name method."""
        llm = QwenLLM(model="qwen-max")
        assert hasattr(llm, "get_model_name")
        assert callable(llm.get_model_name)
        assert llm.get_model_name() == "qwen-max"

    def test_openai_llm_has_chat_method(self):
        """Test OpenAILLM has chat method."""
        llm = OpenAILLM(model="gpt-4")
        assert hasattr(llm, "chat")
        assert callable(llm.chat)

    def test_openai_llm_has_get_model_name(self):
        """Test OpenAILLM has get_model_name method."""
        llm = OpenAILLM(model="gpt-4")
        assert hasattr(llm, "get_model_name")
        assert callable(llm.get_model_name)
        assert llm.get_model_name() == "gpt-4"

    def test_ollama_llm_has_chat_method(self):
        """Test OllamaLLM has chat method."""
        llm = OllamaLLM(model="llama2")
        assert hasattr(llm, "chat")
        assert callable(llm.chat)

    def test_ollama_llm_has_get_model_name(self):
        """Test OllamaLLM has get_model_name method."""
        llm = OllamaLLM(model="llama2")
        assert hasattr(llm, "get_model_name")
        assert callable(llm.get_model_name)
        assert llm.get_model_name() == "llama2"
