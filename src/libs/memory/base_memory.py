"""Base Memory interfaces for Working, Semantic, and Episodic memory."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseWorkingMemory(ABC):
    """Abstract base class for Working Memory (短期工作记忆)."""

    @abstractmethod
    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get working memory state for a session.

        Args:
            session_id: The session identifier.

        Returns:
            The memory state dict or None if not found.
        """
        pass

    @abstractmethod
    def set(self, session_id: str, state: Dict[str, Any]) -> None:
        """Set working memory state for a session.

        Args:
            session_id: The session identifier.
            state: The memory state to store.
        """
        pass

    @abstractmethod
    def delete(self, session_id: str) -> None:
        """Delete working memory for a session.

        Args:
            session_id: The session identifier.
        """
        pass


class BaseSemanticMemory(ABC):
    """Abstract base class for Semantic Memory (长期语义记忆 - 患者档案)."""

    @abstractmethod
    def get(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient profile from semantic memory.

        Args:
            patient_id: The patient identifier.

        Returns:
            The patient profile dict or None if not found.
        """
        pass

    @abstractmethod
    def upsert(self, patient_id: str, profile: Dict[str, Any]) -> None:
        """Insert or update patient profile.

        Args:
            patient_id: The patient identifier.
            profile: The patient profile to store.
        """
        pass

    @abstractmethod
    def delete(self, patient_id: str) -> None:
        """Delete patient profile.

        Args:
            patient_id: The patient identifier.
        """
        pass


class BaseEpisodicMemory(ABC):
    """Abstract base class for Episodic Memory (历史情景记忆)."""

    @abstractmethod
    def add(
        self, patient_id: str, summary: str, metadata: Dict[str, Any] = None
    ) -> str:
        """Add an episodic memory entry.

        Args:
            patient_id: The patient identifier.
            summary: The episode summary text.
            metadata: Optional metadata (timestamp, visit_id, etc.).

        Returns:
            The episode ID.
        """
        pass

    @abstractmethod
    def search(
        self, patient_id: str, query_vector: List[float], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search episodic memory for similar episodes.

        Args:
            patient_id: The patient identifier.
            query_vector: The query embedding vector.
            top_k: Number of results to return.

        Returns:
            List of matching episodes with scores.
        """
        pass

    @abstractmethod
    def get_by_patient(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all episodes for a patient.

        Args:
            patient_id: The patient identifier.

        Returns:
            List of episodes.
        """
        pass
