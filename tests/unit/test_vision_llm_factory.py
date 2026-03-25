"""Tests for Vision LLM Factory."""

from unittest.mock import MagicMock

import pytest

from src.core.settings import Settings
from src.libs.llm.base_vision_llm import BaseVisionLLM
from src.libs.llm.llm_factory import LLMFactory
from src.libs.llm.qwen_vl_llm import QwenVLLM


class FakeVisionLLM(BaseVisionLLM):
    """Fake Vision LLM for testing."""

    def __init__(self, model: str = "fake-vl", api_key: str = None):
        self.model = model
        self.api_key = api_key

    def chat_with_image(self, text: str, image, **kwargs) -> str:
        return f"fake response for: {text}"

    def get_model_name(self) -> str:
        return self.model


class TestVisionLLMFactory:
    """Test Vision LLM factory methods."""

    def test_create_qwen_vl(self):
        """Test creating a Qwen VL LLM."""
        settings = Settings()
        settings.vision_llm.provider = "dashscope"
        settings.vision_llm.model = "qwen-vl-max"
        settings.llm.api_key = "test-key"

        vl = LLMFactory.create_vision_llm(settings)
        assert isinstance(vl, QwenVLLM)
        assert vl.model == "qwen-vl-max"

    def test_create_unsupported_vision_provider_raises_error(self):
        """Test that unsupported Vision provider raises ValueError."""
        settings = Settings()
        settings.vision_llm.provider = "unsupported"
        settings.vision_llm.model = "some-model"

        with pytest.raises(ValueError) as exc_info:
            LLMFactory.create_vision_llm(settings)
        assert "Unsupported Vision LLM provider" in str(exc_info.value)

    def test_register_vision_provider(self):
        """Test registering a new Vision provider."""
        LLMFactory.register_vision_provider("fake", FakeVisionLLM)

        settings = Settings()
        settings.vision_llm.provider = "fake"
        settings.vision_llm.model = "fake-vl"
        settings.llm.api_key = "test-key"

        vl = LLMFactory.create_vision_llm(settings)
        assert isinstance(vl, FakeVisionLLM)


class TestBaseVisionLLMInterface:
    """Test that Vision LLM implementations conform to BaseVisionLLM interface."""

    def test_qwen_vl_has_chat_with_image(self):
        """Test QwenVLLM has chat_with_image method."""
        vl = QwenVLLM(model="qwen-vl-max")
        assert hasattr(vl, "chat_with_image")
        assert callable(vl.chat_with_image)

    def test_qwen_vl_has_get_model_name(self):
        """Test QwenVLLM has get_model_name method."""
        vl = QwenVLLM(model="qwen-vl-max")
        assert hasattr(vl, "get_model_name")
        assert callable(vl.get_model_name)
        assert vl.get_model_name() == "qwen-vl-max"

    def test_qwen_vl_accepts_string_image_path(self):
        """Test QwenVLLM accepts string image path."""
        vl = QwenVLLM(model="qwen-vl-max")
        # Just verify the method signature accepts str
        import inspect

        sig = inspect.signature(vl.chat_with_image)
        assert "text" in sig.parameters
        assert "image" in sig.parameters
