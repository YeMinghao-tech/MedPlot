"""Configuration settings for MedPilot.

Loads settings from config/settings.yaml and validates required fields.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class SettingsError(Exception):
    """Raised when settings validation fails."""

    pass


@dataclass
class LLMConfig:
    provider: str = "dashscope"
    model: str = "qwen-max"
    api_key: Optional[str] = None


@dataclass
class VisionLLMConfig:
    provider: str = "dashscope"
    model: str = "qwen-vl-max"


@dataclass
class EmbeddingConfig:
    provider: str = "dashscope"
    model: str = "text-embedding-v1"


@dataclass
class VectorStoreConfig:
    backend: str = "chroma"
    persist_path: str = "./data/db/chroma"


@dataclass
class RetrievalConfig:
    sparse_backend: str = "bm25"
    fusion_algorithm: str = "rrf"
    top_k_dense: int = 20
    top_k_sparse: int = 20
    top_k_final: int = 10
    rerank_backend: str = "cross_encoder"
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    confidence_threshold: float = 0.7


@dataclass
class MemoryWorkingConfig:
    backend: str = "in_memory"


@dataclass
class MemorySemanticConfig:
    backend: str = "sqlite"
    db_path: str = "./data/db/patient_profiles.db"


@dataclass
class MemoryEpisodicConfig:
    backend: str = "chroma"
    collection: str = "episodic_memory"
    metadata_db: str = "./data/db/episodic_metadata.db"


@dataclass
class MemoryConfig:
    working: MemoryWorkingConfig = field(default_factory=MemoryWorkingConfig)
    semantic: MemorySemanticConfig = field(default_factory=MemorySemanticConfig)
    episodic: MemoryEpisodicConfig = field(default_factory=MemoryEpisodicConfig)


@dataclass
class HISConfig:
    backend: str = "mock"
    mock_db_path: str = "./data/db/his_mock.db"
    use_wal: bool = True
    api_base: str = "http://localhost:8080/his"
    timeout: int = 5


@dataclass
class APIConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    websocket_enabled: bool = True


@dataclass
class ObservabilityConfig:
    enabled: bool = True
    log_file: str = "logs/traces.jsonl"
    audit_log_file: str = "logs/audit_logs.jsonl"
    detail_level: str = "standard"


@dataclass
class DashboardConfig:
    enabled: bool = True
    port: int = 8501


@dataclass
class Settings:
    llm: LLMConfig = field(default_factory=LLMConfig)
    vision_llm: VisionLLMConfig = field(default_factory=VisionLLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    his: HISConfig = field(default_factory=HISConfig)
    api: APIConfig = field(default_factory=APIConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)


def _resolve_env_vars(value: Any) -> Any:
    """Resolve environment variables in a string value.

    Supports ${VAR_NAME} and ${VAR_NAME:default} syntax.
    """
    if isinstance(value, str):
        pattern = r"\$\{([^}:]+)(?::([^}]*))?\}"

        def replacer(match):
            var_name = match.group(1)
            default = match.group(2) if match.group(2) is not None else ""
            return os.environ.get(var_name, default)

        return re.sub(pattern, replacer, value)
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


def _dict_to_settings(data: Dict[str, Any]) -> Settings:
    """Convert a dictionary to a Settings object."""
    return Settings(
        llm=LLMConfig(**data.get("llm", {})),
        vision_llm=VisionLLMConfig(**data.get("vision_llm", {})),
        embedding=EmbeddingConfig(**data.get("embedding", {})),
        vector_store=VectorStoreConfig(**data.get("vector_store", {})),
        retrieval=RetrievalConfig(**data.get("retrieval", {})),
        memory=MemoryConfig(
            working=MemoryWorkingConfig(**data.get("memory", {}).get("working", {})),
            semantic=MemorySemanticConfig(**data.get("memory", {}).get("semantic", {})),
            episodic=MemoryEpisodicConfig(**data.get("memory", {}).get("episodic", {})),
        ),
        his=HISConfig(**data.get("his", {})),
        api=APIConfig(**data.get("api", {})),
        observability=ObservabilityConfig(**data.get("observability", {})),
        dashboard=DashboardConfig(**data.get("dashboard", {})),
    )


def load_settings(path: str = "config/settings.yaml") -> Settings:
    """Load settings from a YAML file.

    Args:
        path: Path to the settings YAML file.

    Returns:
        Settings object.

    Raises:
        SettingsError: If the file cannot be loaded or is invalid.
    """
    settings_path = Path(path)
    if not settings_path.exists():
        raise SettingsError(f"Settings file not found: {path}")

    with open(settings_path, "r") as f:
        raw_data = yaml.safe_load(f)

    if raw_data is None:
        raise SettingsError(f"Settings file is empty: {path}")

    data = _resolve_env_vars(raw_data)
    settings = _dict_to_settings(data)

    validate_settings(settings)

    return settings


def _is_empty(value) -> bool:
    """Check if a value is None or empty string."""
    return value is None or (isinstance(value, str) and value == "")


def validate_settings(settings: Settings) -> None:
    """Validate that required settings are present.

    Args:
        settings: Settings object to validate.

    Raises:
        SettingsError: If a required field is missing or invalid.
    """
    required_llm_fields = ["provider", "model"]
    for field_name in required_llm_fields:
        if _is_empty(getattr(settings.llm, field_name, None)):
            raise SettingsError(f"LLM config is missing required field: {field_name}")

    required_embedding_fields = ["provider", "model"]
    for field_name in required_embedding_fields:
        if _is_empty(getattr(settings.embedding, field_name, None)):
            raise SettingsError(f"Embedding config is missing required field: {field_name}")

    required_vector_store_fields = ["backend"]
    for field_name in required_vector_store_fields:
        if not hasattr(settings.vector_store, field_name) or getattr(settings.vector_store, field_name) is None:
            raise SettingsError(f"VectorStore config is missing required field: {field_name}")

    required_retrieval_fields = ["sparse_backend", "fusion_algorithm", "top_k_final"]
    for field_name in required_retrieval_fields:
        if not hasattr(settings.retrieval, field_name) or getattr(settings.retrieval, field_name) is None:
            raise SettingsError(f"Retrieval config is missing required field: {field_name}")

    required_memory_fields = ["working", "semantic", "episodic"]
    for field_name in required_memory_fields:
        if not hasattr(settings.memory, field_name) or getattr(settings.memory, field_name) is None:
            raise SettingsError(f"Memory config is missing required field: {field_name}")

    required_his_fields = ["backend"]
    for field_name in required_his_fields:
        if not hasattr(settings.his, field_name) or getattr(settings.his, field_name) is None:
            raise SettingsError(f"HIS config is missing required field: {field_name}")

    required_api_fields = ["host", "port"]
    for field_name in required_api_fields:
        if not hasattr(settings.api, field_name) or getattr(settings.api, field_name) is None:
            raise SettingsError(f"API config is missing required field: {field_name}")
