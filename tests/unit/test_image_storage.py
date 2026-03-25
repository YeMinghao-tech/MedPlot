"""Tests for image storage."""

import tempfile

from src.ingestion.storage.image_storage import ImageStorage


class TestImageStorage:
    """Test ImageStorage functionality."""

    def test_save_and_get_path(self):
        """Test saving an image and retrieving its path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ImageStorage(
                storage_dir=f"{tmpdir}/images",
                db_path=f"{tmpdir}/image_index.db",
            )

            image_data = b"fake image data"
            image_id = storage.save(image_data, "test.png", collection="test")

            assert image_id is not None

            path = storage.get_path(image_id)
            assert path is not None
            assert "test.png" in path or image_id in path

    def test_get_path_not_found(self):
        """Test getting path for non-existent image."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ImageStorage(
                storage_dir=f"{tmpdir}/images",
                db_path=f"{tmpdir}/image_index.db",
            )

            path = storage.get_path("nonexistent-id")
            assert path is None

    def test_get_by_collection(self):
        """Test getting images by collection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ImageStorage(
                storage_dir=f"{tmpdir}/images",
                db_path=f"{tmpdir}/image_index.db",
            )

            storage.save(b"data1", "img1.png", collection="medical")
            storage.save(b"data2", "img2.png", collection="medical")
            storage.save(b"data3", "img3.png", collection="other")

            results = storage.get_by_collection("medical")
            assert len(results) == 2

            results = storage.get_by_collection("other")
            assert len(results) == 1

    def test_delete(self):
        """Test deleting an image."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ImageStorage(
                storage_dir=f"{tmpdir}/images",
                db_path=f"{tmpdir}/image_index.db",
            )

            image_id = storage.save(b"image data", "test.png")

            # Should exist before delete
            assert storage.get_path(image_id) is not None

            # Delete
            result = storage.delete(image_id)
            assert result is True

            # Should not exist after delete
            assert storage.get_path(image_id) is None

    def test_delete_not_found(self):
        """Test deleting non-existent image."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ImageStorage(
                storage_dir=f"{tmpdir}/images",
                db_path=f"{tmpdir}/image_index.db",
            )

            result = storage.delete("nonexistent-id")
            assert result is False

    def test_file_extension_handling(self):
        """Test that file extensions are handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ImageStorage(
                storage_dir=f"{tmpdir}/images",
                db_path=f"{tmpdir}/image_index.db",
            )

            # Save with no extension
            image_id = storage.save(b"data", "file", collection="test")
            path = storage.get_path(image_id)
            # Should default to .png
            assert ".png" in path or ".jpg" in path

            # Save with proper extension
            image_id = storage.save(b"data", "file.jpg", collection="test")
            path = storage.get_path(image_id)
            assert ".jpg" in path
