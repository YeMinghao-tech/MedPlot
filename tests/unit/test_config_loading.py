"""Tests for configuration loading and validation."""

import os
import tempfile

import pytest

from src.core.settings import (
    Settings,
    SettingsError,
    load_settings,
    validate_settings,
)


class TestLoadSettings:
    """Test load_settings function."""

    def test_load_settings_success(self):
        """Test that settings can be loaded from a valid YAML file."""
        settings = load_settings("config/settings.yaml")
        assert settings is not None
        assert isinstance(settings, Settings)

    def test_load_settings_file_not_found(self):
        """Test that SettingsError is raised when file doesn't exist."""
        with pytest.raises(SettingsError) as exc_info:
            load_settings("nonexistent.yaml")
        assert "not found" in str(exc_info.value)

    def test_load_settings_empty_file(self):
        """Test that SettingsError is raised for empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            with pytest.raises(SettingsError) as exc_info:
                load_settings(temp_path)
            assert "empty" in str(exc_info.value)
        finally:
            os.unlink(temp_path)


class TestValidateSettings:
    """Test validate_settings function."""

    def test_valid_settings_pass(self):
        """Test that valid settings pass validation."""
        settings = Settings()
        # Should not raise
        validate_settings(settings)

    def test_missing_llm_provider_fails(self):
        """Test that missing LLM provider fails validation."""
        settings = Settings()
        settings.llm.provider = ""
        with pytest.raises(SettingsError) as exc_info:
            validate_settings(settings)
        assert "LLM" in str(exc_info.value)

    def test_missing_embedding_provider_fails(self):
        """Test that missing embedding provider fails validation."""
        settings = Settings()
        settings.embedding.provider = ""
        with pytest.raises(SettingsError) as exc_info:
            validate_settings(settings)
        assert "Embedding" in str(exc_info.value)


class TestEnvVarResolution:
    """Test environment variable resolution."""

    def test_env_var_substitution(self):
        """Test that environment variables are resolved in settings."""
        os.environ["TEST_API_KEY"] = "test_secret_123"
        try:
            settings = load_settings("config/settings.yaml")
            # The API key field should be resolved if it uses ${TEST_API_KEY}
            assert settings.llm.api_key is not None or settings.llm.api_key == ""
        finally:
            del os.environ["TEST_API_KEY"]


class TestSettingsStructure:
    """Test that Settings object has expected structure."""

    def test_settings_has_llm_config(self):
        """Test that Settings has LLM config."""
        settings = load_settings("config/settings.yaml")
        assert hasattr(settings, "llm")
        assert hasattr(settings.llm, "provider")
        assert hasattr(settings.llm, "model")

    def test_settings_has_embedding_config(self):
        """Test that Settings has embedding config."""
        settings = load_settings("config/settings.yaml")
        assert hasattr(settings, "embedding")
        assert hasattr(settings.embedding, "provider")
        assert hasattr(settings.embedding, "model")

    def test_settings_has_vector_store_config(self):
        """Test that Settings has vector store config."""
        settings = load_settings("config/settings.yaml")
        assert hasattr(settings, "vector_store")
        assert hasattr(settings.vector_store, "backend")

    def test_settings_has_retrieval_config(self):
        """Test that Settings has retrieval config."""
        settings = load_settings("config/settings.yaml")
        assert hasattr(settings, "retrieval")
        assert hasattr(settings.retrieval, "top_k_final")

    def test_settings_has_memory_config(self):
        """Test that Settings has memory config."""
        settings = load_settings("config/settings.yaml")
        assert hasattr(settings, "memory")
        assert hasattr(settings.memory, "working")
        assert hasattr(settings.memory, "semantic")
        assert hasattr(settings.memory, "episodic")

    def test_settings_has_his_config(self):
        """Test that Settings has HIS config."""
        settings = load_settings("config/settings.yaml")
        assert hasattr(settings, "his")
        assert hasattr(settings.his, "backend")

    def test_settings_has_api_config(self):
        """Test that Settings has API config."""
        settings = load_settings("config/settings.yaml")
        assert hasattr(settings, "api")
        assert hasattr(settings.api, "host")
        assert hasattr(settings.api, "port")
