"""Semantic memory for long-term patient profiles."""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class SemanticMemory:
    """Long-term semantic memory for patient profiles.

    Stores structured patient information in SQLite:
    - Patient demographics
    - Medical history
    - Allergies
    - Current medications
    - etc.
    """

    def __init__(self, db_path: str = "./data/db/patient_profiles.db"):
        """Initialize semantic memory.

        Args:
            db_path: Path to SQLite database.
        """
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patient_profiles (
                    patient_id TEXT PRIMARY KEY,
                    profile_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()

    def get(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient profile.

        Args:
            patient_id: Patient identifier.

        Returns:
            Profile dict or None if not found.
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                "SELECT profile_json FROM patient_profiles WHERE patient_id = ?",
                (patient_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return json.loads(row[0])
            return None

    def upsert(self, patient_id: str, profile: Dict[str, Any]):
        """Insert or update patient profile.

        Merge strategy: existing fields are preserved unless
        explicitly overridden in the new profile.

        Args:
            patient_id: Patient identifier.
            profile: Profile data to upsert.
        """
        # Get existing profile for merge
        existing = self.get(patient_id)
        merged = self._merge_profiles(existing, profile)

        profile_json = json.dumps(merged, ensure_ascii=False)

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """
                INSERT INTO patient_profiles (patient_id, profile_json, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(patient_id) DO UPDATE SET
                    profile_json = excluded.profile_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (patient_id, profile_json)
            )
            conn.commit()
            conn.close()

    def _merge_profiles(
        self,
        existing: Optional[Dict[str, Any]],
        new_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge existing profile with new data.

        Args:
            existing: Existing profile or None.
            new_profile: New profile data.

        Returns:
            Merged profile.
        """
        if not existing:
            return new_profile

        merged = existing.copy()

        # Merge top-level fields
        for key, value in new_profile.items():
            if key in merged:
                # Special handling for lists (append unique)
                if isinstance(value, list) and isinstance(merged[key], list):
                    for item in value:
                        if item not in merged[key]:
                            merged[key].append(item)
                # Special handling for dicts (deep merge)
                elif isinstance(value, dict) and isinstance(merged[key], dict):
                    merged[key].update(value)
                # Otherwise overwrite
                else:
                    merged[key] = value
            else:
                merged[key] = value

        return merged

    def delete(self, patient_id: str):
        """Delete patient profile.

        Args:
            patient_id: Patient identifier.
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "DELETE FROM patient_profiles WHERE patient_id = ?",
                (patient_id,)
            )
            conn.commit()
            conn.close()

    def exists(self, patient_id: str) -> bool:
        """Check if patient profile exists.

        Args:
            patient_id: Patient identifier.

        Returns:
            True if exists.
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                "SELECT 1 FROM patient_profiles WHERE patient_id = ? LIMIT 1",
                (patient_id,)
            )
            exists = cursor.fetchone() is not None
            conn.close()
            return exists
