"""Chroma-based Episodic Memory implementation."""

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.libs.memory.base_memory import BaseEpisodicMemory


class ChromaEpisodicMemory(BaseEpisodicMemory):
    """Chroma implementation of Episodic Memory for historical episodes."""

    def __init__(
        self,
        persist_path: str = "./data/db/episodic_chroma",
        collection: str = "episodic_memory",
    ):
        """Initialize Chroma Episodic Memory.

        Args:
            persist_path: Path to persist Chroma database.
            collection: Collection name.
        """
        self.persist_path = persist_path
        self.collection_name = collection
        self._client = None
        self._collection_cache: Dict[str, Any] = {}

    def _get_client(self):
        """Get or create the Chroma client."""
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings as ChromaSettings
            except ImportError:
                raise ImportError(
                    "chromadb package is required for Chroma Episodic Memory. "
                    "Install it with: pip install chromadb"
                )
            self._client = chromadb.Client(
                ChromaSettings(
                    persist_directory=self.persist_path,
                    anonymized_telemetry=False,
                )
            )
        return self._client

    def _get_collection(self):
        """Get or create the collection."""
        if self.collection_name not in self._collection_cache:
            client = self._get_client()
            self._collection_cache[self.collection_name] = client.get_or_create_collection(
                name=self.collection_name
            )
        return self._collection_cache[self.collection_name]

    def add(
        self, patient_id: str, summary: str, metadata: Dict[str, Any] = None
    ) -> str:
        """Add an episodic memory entry."""
        episode_id = str(uuid.uuid4())
        metadata = metadata or {}
        metadata["patient_id"] = patient_id

        collection = self._get_collection()
        collection.add(
            ids=[episode_id],
            embeddings=[[0.0] * 128],  # Placeholder - should use actual embedding
            documents=[summary],
            metadatas=[metadata],
        )
        return episode_id

    def search(
        self, patient_id: str, query_vector: List[float], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search episodic memory for similar episodes."""
        collection = self._get_collection()

        # Query with pre-filter for patient_id
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where={"patient_id": patient_id},
        )

        episodes = []
        if results and results.get("ids"):
            for i in range(len(results["ids"][0])):
                episodes.append({
                    "id": results["ids"][0][i],
                    "summary": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": results.get("distances", [[]])[0][i],
                })
        return episodes

    def get_by_patient(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all episodes for a patient."""
        collection = self._get_collection()

        results = collection.get(where={"patient_id": patient_id})

        episodes = []
        if results and results.get("ids"):
            for i in range(len(results["ids"])):
                episodes.append({
                    "id": results["ids"][i],
                    "summary": results["documents"][i],
                    "metadata": results["metadatas"][i],
                })
        return episodes
