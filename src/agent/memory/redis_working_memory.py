"""Redis-backed working memory store."""

import json
from typing import Dict, Optional
import redis

from src.agent.memory.working_memory import WorkingMemory, WorkingMemoryStore, ConversationTurn


class RedisWorkingMemoryStore(WorkingMemoryStore):
    """Working memory store backed by Redis.

    Provides persistence across process restarts.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        key_prefix: str = "medpilot:wm:",
        ttl: int = 3600,
    ):
        """Initialize Redis-backed store.

        Args:
            host: Redis host.
            port: Redis port.
            db: Redis database number.
            password: Optional Redis password.
            key_prefix: Prefix for all keys.
            ttl: Time-to-live for memory entries in seconds.
        """
        self._redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
        )
        self._key_prefix = key_prefix
        self._ttl = ttl
        self._local_cache: Dict[str, WorkingMemory] = {}

    def _make_key(self, session_id: str) -> str:
        """Make Redis key for session."""
        return f"{self._key_prefix}{session_id}"

    def get(self, session_id: str) -> WorkingMemory:
        """Get or create working memory for session.

        Args:
            session_id: Session identifier.

        Returns:
            WorkingMemory instance.
        """
        # Check local cache first
        if session_id in self._local_cache:
            return self._local_cache[session_id]

        # Try to load from Redis
        key = self._make_key(session_id)
        data = self._redis.get(key)

        if data:
            memory = self._deserialize(data)
            memory.session_id = session_id
        else:
            memory = WorkingMemory(session_id=session_id)

        self._local_cache[session_id] = memory
        return memory

    def delete(self, session_id: str):
        """Delete working memory for session.

        Args:
            session_id: Session identifier.
        """
        # Remove from local cache
        if session_id in self._local_cache:
            del self._local_cache[session_id]

        # Remove from Redis
        key = self._make_key(session_id)
        self._redis.delete(key)

    def exists(self, session_id: str) -> bool:
        """Check if session exists in Redis.

        Args:
            session_id: Session identifier.

        Returns:
            True if session exists.
        """
        key = self._make_key(session_id)
        return self._redis.exists(key) > 0

    def save(self, session_id: str):
        """Explicitly save session to Redis (normally auto-saved on changes).

        Args:
            session_id: Session identifier.
        """
        if session_id not in self._local_cache:
            return

        memory = self._local_cache[session_id]
        key = self._make_key(session_id)
        data = self._serialize(memory)
        self._redis.setex(key, self._ttl, data)

    def _serialize(self, memory: WorkingMemory) -> str:
        """Serialize working memory to JSON."""
        return json.dumps({
            "patient_id": memory.patient_id,
            "symptom_tree": memory.symptom_tree,
            "message_history": [
                {"role": t.role, "content": t.content, "timestamp": t.timestamp}
                for t in memory.message_history
            ],
            "current_intent": memory.current_intent,
            "context": memory.context,
        }, ensure_ascii=False)

    def _deserialize(self, data: str) -> WorkingMemory:
        """Deserialize working memory from JSON."""
        obj = json.loads(data)
        memory = WorkingMemory(session_id="")

        memory.patient_id = obj.get("patient_id")
        memory.symptom_tree = obj.get("symptom_tree", {})
        memory.current_intent = obj.get("current_intent")
        memory.context = obj.get("context", {})

        for t in obj.get("message_history", []):
            memory.message_history.append(ConversationTurn(
                role=t["role"],
                content=t["content"],
                timestamp=t.get("timestamp", ""),
            ))

        return memory
