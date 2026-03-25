"""Memory factory for creating memory instances based on configuration."""

from typing import Optional

from src.libs.vector_store.base_vector_store import BaseVectorStore
from src.agent.memory.working_memory import WorkingMemory, WorkingMemoryStore
from src.agent.memory.semantic_memory import SemanticMemory
from src.agent.memory.episodic_memory import EpisodicMemory


class MemoryFactory:
    """Factory for creating memory instances.

    Supports configuration-driven backend selection:
    - working: in_memory (default) or redis (future)
    - semantic: sqlite (default)
    - episodic: chroma (default)
    """

    @staticmethod
    def create_working(settings: Optional[dict] = None) -> WorkingMemoryStore:
        """Create working memory store.

        Args:
            settings: Optional settings dict with 'backend' key.

        Returns:
            WorkingMemoryStore instance.
        """
        backend = (settings or {}).get("backend", "in_memory")

        if backend == "redis":
            # TODO: Implement RedisWorkingMemoryStore
            raise NotImplementedError("Redis working memory not yet implemented")
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
