"""Image storage for medical images with SQLite indexing."""

import hashlib
import os
import shutil
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class ImageStorage:
    """Stores medical images and maintains SQLite index.

    Supports WAL mode for better concurrency.
    """

    def __init__(
        self,
        storage_dir: str = "./data/images",
        db_path: str = "./data/db/image_index.db",
        use_wal: bool = True,
    ):
        """Initialize image storage.

        Args:
            storage_dir: Directory to store image files.
            db_path: Path to SQLite index database.
            use_wal: Whether to use WAL mode.
        """
        self.storage_dir = storage_dir
        self.db_path = db_path
        self.use_wal = use_wal
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        Path(self.storage_dir).mkdir(parents=True, exist_ok=True)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            if self.use_wal:
                conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    image_id TEXT PRIMARY KEY,
                    original_filename TEXT,
                    storage_path TEXT NOT NULL,
                    collection TEXT,
                    file_hash TEXT,
                    file_size INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()

    def save(
        self,
        image_data: bytes,
        original_filename: str,
        collection: str = "default",
    ) -> str:
        """Save an image and return its ID.

        Args:
            image_data: Raw image bytes.
            original_filename: Original filename.
            collection: Collection name for organization.

        Returns:
            Image ID.
        """
        # Generate image ID
        image_id = str(uuid.uuid4())

        # Compute hash for deduplication
        file_hash = hashlib.sha256(image_data).hexdigest()

        # Determine file extension from filename
        ext = Path(original_filename).suffix.lower()
        if not ext or ext not in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
            ext = ".png"  # Default to PNG

        # Storage path
        collection_dir = Path(self.storage_dir) / collection
        collection_dir.mkdir(parents=True, exist_ok=True)
        storage_path = collection_dir / f"{image_id}{ext}"

        with self._lock:
            # Save file
            with open(storage_path, "wb") as f:
                f.write(image_data)

            # Update index
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            if self.use_wal:
                conn.execute("PRAGMA journal_mode=WAL")

            conn.execute(
                """
                INSERT INTO images (image_id, original_filename, storage_path, collection, file_hash, file_size)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (image_id, original_filename, str(storage_path), collection, file_hash, len(image_data)),
            )
            conn.commit()
            conn.close()

        return image_id

    def get_path(self, image_id: str) -> Optional[str]:
        """Get the storage path for an image.

        Args:
            image_id: Image ID.

        Returns:
            Storage path, or None if not found.
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.execute(
                "SELECT storage_path FROM images WHERE image_id = ?",
                (image_id,),
            )
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None

    def get_by_collection(self, collection: str) -> List[Dict[str, Any]]:
        """Get all images in a collection.

        Args:
            collection: Collection name.

        Returns:
            List of image info dicts.
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.execute(
                """
                SELECT image_id, original_filename, collection, file_hash, file_size, created_at
                FROM images WHERE collection = ?
                """,
                (collection,),
            )
            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "image_id": row[0],
                    "original_filename": row[1],
                    "collection": row[2],
                    "file_hash": row[3],
                    "file_size": row[4],
                    "created_at": row[5],
                }
                for row in rows
            ]

    def delete(self, image_id: str) -> bool:
        """Delete an image.

        Args:
            image_id: Image ID.

        Returns:
            True if deleted, False if not found.
        """
        path = self.get_path(image_id)
        if not path:
            return False

        # Delete file
        if Path(path).exists():
            os.remove(path)

        # Delete from index
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("DELETE FROM images WHERE image_id = ?", (image_id,))
            conn.commit()
            conn.close()

        return True
