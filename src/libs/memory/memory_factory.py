"""Memory Factory for creating Memory instances based on configuration."""

from typing import Type

from src.core.settings import Settings
from src.libs.memory.base_memory import (
    BaseEpisodicMemory,
    BaseSemanticMemory,
    BaseWorkingMemory,
)
from src.libs.memory.chroma_memory import ChromaEpisodicMemory
from src.libs.memory.in_memory_working import InMemoryWorkingMemory
from src.libs.memory.sqlite_memory import SQLiteSemanticMemory


class MemoryFactory:
    """Factory for creating Memory instances based on configuration."""

    @classmethod
    def create_working(cls, settings: Settings) -> BaseWorkingMemory:
        """Create a Working Memory instance.

        Args:
            settings: Settings object.

        Returns:
            A Working Memory instance.
        """
        backend = settings.memory.working.backend.lower()

        if backend == "in_memory":
            return InMemoryWorkingMemory()
        elif backend == "redis":
            # Redis implementation would go here
            raise NotImplementedError("Redis working memory not yet implemented")
        else:
            raise ValueError(f"Unsupported working memory backend: {backend}")

    @classmethod
    def create_semantic(cls, settings: Settings) -> BaseSemanticMemory:
        """Create a Semantic Memory instance.

        Args:
            settings: Settings object.

        Returns:
            A Semantic Memory instance.
        """
        backend = settings.memory.semantic.backend.lower()

        if backend == "sqlite":
            return SQLiteSemanticMemory(db_path=settings.memory.semantic.db_path)
        elif backend == "postgresql":
            raise NotImplementedError("PostgreSQL semantic memory not yet implemented")
        else:
            raise ValueError(f"Unsupported semantic memory backend: {backend}")

    @classmethod
    def create_episodic(cls, settings: Settings) -> BaseEpisodicMemory:
        """Create an Episodic Memory instance.

        Args:
            settings: Settings object.

        Returns:
            An Episodic Memory instance.
        """
        backend = settings.memory.episodic.backend.lower()

        if backend == "chroma":
            return ChromaEpisodicMemory(
                persist_path=settings.memory.episodic.metadata_db.replace(
                    "_metadata.db", "_chroma"
                ),
                collection=settings.memory.episodic.collection,
            )
        else:
            raise ValueError(f"Unsupported episodic memory backend: {backend}")
