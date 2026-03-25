"""Memory factory for creating memory instances based on configuration."""

from typing import Optional

from src.libs.vector_store.base_vector_store import BaseVectorStore
from src.agent.memory.working_memory import WorkingMemory, WorkingMemoryStore
from src.agent.memory.semantic_memory import SemanticMemory
from src.agent.memory.episodic_memory import EpisodicMemory


class MemoryFactory:
    """Factory for creating memory instances.

    Supports configuration-driven backend selection:
    - working: in_memory (default) or redis
    - semantic: sqlite (default)
    - episodic: chroma (default)
    """

    @staticmethod
    def create_working(settings: Optional[dict] = None) -> WorkingMemoryStore:
        """Create working memory store.

        Args:
            settings: Optional settings dict with keys:
                - backend: "in_memory" or "redis"
                - redis_host, redis_port, redis_db, redis_password, ttl (for redis)

        Returns:
            WorkingMemoryStore instance.
        """
        backend = (settings or {}).get("backend", "in_memory")

        if backend == "redis":
            from src.agent.memory.redis_working_memory import RedisWorkingMemoryStore
            return RedisWorkingMemoryStore(
                host=(settings or {}).get("redis_host", "localhost"),
                port=(settings or {}).get("redis_port", 6379),
                db=(settings or {}).get("redis_db", 0),
                password=(settings or {}).get("redis_password"),
                key_prefix=(settings or {}).get("key_prefix", "medpilot:wm:"),
                ttl=(settings or {}).get("ttl", 3600),
            )
        elif backend == "in_memory":
            return WorkingMemoryStore()
        else:
            raise ValueError(f"Unknown working memory backend: {backend}")

    @staticmethod
    def create_semantic(settings: Optional[dict] = None) -> SemanticMemory:
        """Create semantic memory.

        Args:
            settings: Optional settings dict with 'db_path' key.

        Returns:
            SemanticMemory instance.
        """
        db_path = (settings or {}).get("db_path", "./data/db/patient_profiles.db")
        return SemanticMemory(db_path=db_path)

    @staticmethod
    def create_episodic(
        vector_store: BaseVectorStore,
        settings: Optional[dict] = None,
    ) -> EpisodicMemory:
        """Create episodic memory.

        Args:
            vector_store: Vector store for embeddings.
            settings: Optional settings dict with 'metadata_db' and 'collection' keys.

        Returns:
            EpisodicMemory instance.
        """
        metadata_db = (settings or {}).get(
            "metadata_db", "./data/db/episodic_metadata.db"
        )
        collection = (settings or {}).get("collection", "episodic_memory")

        return EpisodicMemory(
            vector_store=vector_store,
            metadata_db_path=metadata_db,
            collection=collection,
        )
