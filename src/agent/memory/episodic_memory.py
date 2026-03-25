"""Episodic memory for historical visit retrieval."""

import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.libs.vector_store.base_vector_store import BaseVectorStore


@dataclass
class Episode:
    """A single episodic memory entry."""

    episode_id: str
    patient_id: str
    session_id: str
    summary: str
    timestamp: str
    metadata: Dict[str, Any]


class EpisodicMemory:
    """Episodic memory for historical visit records.

    Stores visit summaries with vector embeddings for similarity search.
    Uses SQLite for metadata and VectorStore for embeddings.
    """

    def __init__(
        self,
        vector_store: BaseVectorStore,
        metadata_db_path: str = "./data/db/episodic_metadata.db",
        collection: str = "episodic_memory",
    ):
        """Initialize episodic memory.

        Args:
            vector_store: Vector store for embeddings.
            metadata_db_path: Path to SQLite metadata database.
            collection: Collection name for vector store.
        """
        self.vector_store = vector_store
        self.metadata_db_path = metadata_db_path
        self.collection = collection
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Initialize metadata database."""
        Path(self.metadata_db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            conn = sqlite3.connect(self.metadata_db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    episode_id TEXT PRIMARY KEY,
                    patient_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata_json TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_episodes_patient
                ON episodes(patient_id)
            """)
            conn.commit()
            conn.close()

    def add(
        self,
        patient_id: str,
        session_id: str,
        summary: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add an episodic memory.

        Args:
            patient_id: Patient identifier.
            session_id: Session identifier.
            summary: Visit summary text.
            embedding: Vector embedding of summary.
            metadata: Optional additional metadata.

        Returns:
            Generated episode ID.
        """
        import uuid
        episode_id = str(uuid.uuid4())

        with self._lock:
            conn = sqlite3.connect(self.metadata_db_path)
            conn.execute(
                """
                INSERT INTO episodes
                (episode_id, patient_id, session_id, summary, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    episode_id,
                    patient_id,
                    session_id,
                    summary,
                    json.dumps(metadata or {}, ensure_ascii=False),
                )
            )
            conn.commit()
            conn.close()

        # Store embedding in vector store
        self.vector_store.upsert(
            records=[{
                "id": episode_id,
                "embedding": embedding,
                "text": summary,
                "metadata": {
                    "patient_id": patient_id,
                    "session_id": session_id,
                },
            }],
            collection=self.collection,
        )

        return episode_id

    def search(
        self,
        patient_id: str,
        query_vector: List[float],
        top_k: int = 5,
    ) -> List[Episode]:
        """Search episodic memories for a patient.

        Args:
            patient_id: Patient identifier.
            query_vector: Query embedding vector.
            top_k: Number of results to return.

        Returns:
            List of matching episodes.
        """
        # Query vector store with metadata filter
        results = self.vector_store.query(
            vector=query_vector,
            top_k=top_k,
            filters={"patient_id": patient_id},
            collection=self.collection,
        )

        if not results:
            return []

        # Retrieve full episodes from metadata
        episode_ids = [r["id"] for r in results]
        episodes = self._get_by_ids(episode_ids)

        # Sort by vector similarity (results are already sorted)
        id_to_score = {r["id"]: r.get("score", 0.0) for r in results}
        for ep in episodes:
            ep.metadata["similarity_score"] = id_to_score.get(ep.episode_id, 0.0)

        return episodes

    def _get_by_ids(self, episode_ids: List[str]) -> List[Episode]:
        """Get episodes by their IDs."""
        if not episode_ids:
            return []

        with self._lock:
            conn = sqlite3.connect(self.metadata_db_path)
            placeholders = ",".join("?" * len(episode_ids))
            cursor = conn.execute(
                f"""
                SELECT episode_id, patient_id, session_id, summary,
                       timestamp, metadata_json
                FROM episodes
                WHERE episode_id IN ({placeholders})
                """,
                episode_ids
            )
            rows = cursor.fetchall()
            conn.close()

        episodes = []
        for row in rows:
            episodes.append(Episode(
                episode_id=row[0],
                patient_id=row[1],
                session_id=row[2],
                summary=row[3],
                timestamp=row[4],
                metadata=json.loads(row[5]) if row[5] else {},
            ))

        return episodes

    def get_patient_history(self, patient_id: str, limit: int = 10) -> List[Episode]:
        """Get recent episode history for a patient.

        Args:
            patient_id: Patient identifier.
            limit: Maximum number of episodes to return.

        Returns:
            List of episodes ordered by timestamp descending.
        """
        with self._lock:
            conn = sqlite3.connect(self.metadata_db_path)
            cursor = conn.execute(
                """
                SELECT episode_id, patient_id, session_id, summary,
                       timestamp, metadata_json
                FROM episodes
                WHERE patient_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (patient_id, limit)
            )
            rows = cursor.fetchall()
            conn.close()

        episodes = []
        for row in rows:
            episodes.append(Episode(
                episode_id=row[0],
                patient_id=row[1],
                session_id=row[2],
                summary=row[3],
                timestamp=row[4],
                metadata=json.loads(row[5]) if row[5] else {},
            ))

        return episodes
