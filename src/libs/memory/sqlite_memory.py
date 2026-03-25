"""SQLite-based Semantic Memory implementation."""

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from src.libs.memory.base_memory import BaseSemanticMemory


class SQLiteSemanticMemory(BaseSemanticMemory):
    """SQLite implementation of Semantic Memory for patient profiles."""

    def __init__(self, db_path: str = "./data/db/patient_profiles.db"):
        """Initialize SQLite Semantic Memory.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patient_profiles (
                    patient_id TEXT PRIMARY KEY,
                    profile TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()

    def get(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient profile from semantic memory."""
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.execute(
                "SELECT profile FROM patient_profiles WHERE patient_id = ?",
                (patient_id,),
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return json.loads(row[0])
            return None

    def upsert(self, patient_id: str, profile: Dict[str, Any]) -> None:
        """Insert or update patient profile."""
        with self._lock:
            # Get existing profile and merge
            existing = self.get(patient_id) if patient_id else None
            if existing:
                # Deep merge - existing fields are preserved unless in new profile
                merged = existing.copy()
                merged.update(profile)
                profile = merged

            profile_json = json.dumps(profile, ensure_ascii=False)
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute(
                """
                INSERT INTO patient_profiles (patient_id, profile, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(patient_id) DO UPDATE SET
                    profile = excluded.profile,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (patient_id, profile_json),
            )
            conn.commit()
            conn.close()

    def delete(self, patient_id: str) -> None:
        """Delete patient profile."""
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute(
                "DELETE FROM patient_profiles WHERE patient_id = ?", (patient_id,)
            )
            conn.commit()
            conn.close()
