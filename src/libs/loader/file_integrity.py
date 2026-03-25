"""File integrity checker for incremental ingestion.

Uses SHA256 to track file changes and avoid re-processing unchanged files.
"""

import hashlib
import sqlite3
import threading
from pathlib import Path
from typing import Optional


class SQLiteIntegrityChecker:
    """SQLite-based file integrity checker for incremental ingestion."""

    def __init__(self, db_path: str = "./data/db/ingestion_history.db"):
        """Initialize the integrity checker.

        Args:
            db_path: Path to the SQLite database for tracking file hashes.
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
                CREATE TABLE IF NOT EXISTS file_hashes (
                    file_path TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    file_size INTEGER,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()

    def compute_sha256(self, file_path: str) -> str:
        """Compute SHA256 hash of a file.

        Args:
            file_path: Path to the file.

        Returns:
            Hex string of the SHA256 hash.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def should_skip(self, file_path: str) -> bool:
        """Check if a file should be skipped (hash unchanged).

        Args:
            file_path: Path to the file.

        Returns:
            True if the file hash matches the stored hash (skip processing).
        """
        current_hash = self.compute_sha256(file_path)
        stored_hash = self._get_stored_hash(file_path)
        return current_hash == stored_hash

    def _get_stored_hash(self, file_path: str) -> Optional[str]:
        """Get the stored hash for a file."""
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.execute(
                "SELECT file_hash FROM file_hashes WHERE file_path = ?",
                (file_path,),
            )
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None

    def mark_success(self, file_path: str, file_hash: Optional[str] = None) -> None:
        """Mark a file as successfully processed.

        Args:
            file_path: Path to the file.
            file_hash: SHA256 hash (computed if not provided).
        """
        if file_hash is None:
            file_hash = self.compute_sha256(file_path)

        file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0

        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute(
                """
                INSERT INTO file_hashes (file_path, file_hash, file_size, processed_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_hash = excluded.file_hash,
                    file_size = excluded.file_size,
                    processed_at = CURRENT_TIMESTAMP
                """,
                (file_path, file_hash, file_size),
            )
            conn.execute(
                """
                INSERT INTO processing_log (file_path, file_hash, status, processed_at)
                VALUES (?, ?, 'success', CURRENT_TIMESTAMP)
                """,
                (file_path, file_hash),
            )
            conn.commit()
            conn.close()

    def mark_failed(self, file_path: str, error_message: str) -> None:
        """Mark a file as failed.

        Args:
            file_path: Path to the file.
            error_message: Error description.
        """
        file_hash = self.compute_sha256(file_path) if Path(file_path).exists() else ""
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute(
                """
                INSERT INTO processing_log (file_path, file_hash, status, error_message, processed_at)
                VALUES (?, ?, 'failed', ?, CURRENT_TIMESTAMP)
                """,
                (file_path, file_hash, error_message),
            )
            conn.commit()
            conn.close()

    def get_processed_files(self) -> list:
        """Get list of all successfully processed files."""
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.execute(
                "SELECT file_path, file_hash, processed_at FROM file_hashes"
            )
            rows = cursor.fetchall()
            conn.close()
            return [{"file_path": r[0], "file_hash": r[1], "processed_at": r[2]} for r in rows]

    def clear(self) -> None:
        """Clear all stored hashes (force re-processing)."""
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("DELETE FROM file_hashes")
            conn.execute("DELETE FROM processing_log")
            conn.commit()
            conn.close()
