"""Tests for file integrity checker."""

import tempfile

import pytest

from src.libs.loader.file_integrity import SQLiteIntegrityChecker


class TestSQLiteIntegrityChecker:
    """Test SQLiteIntegrityChecker functionality."""

    def test_compute_sha256(self):
        """Test SHA256 computation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test_integrity.db"
            checker = SQLiteIntegrityChecker(db_path=db_path)

            # Create a test file
            file_path = f"{tmpdir}/test.txt"
            with open(file_path, "w") as f:
                f.write("Hello, World!")

            hash1 = checker.compute_sha256(file_path)
            assert len(hash1) == 64  # SHA256 produces 64 hex chars
            assert isinstance(hash1, str)

            # Same content should produce same hash
            hash2 = checker.compute_sha256(file_path)
            assert hash1 == hash2

    def test_should_skip_new_file(self):
        """Test should_skip returns False for new files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test_integrity.db"
            checker = SQLiteIntegrityChecker(db_path=db_path)

            file_path = f"{tmpdir}/new_file.txt"
            with open(file_path, "w") as f:
                f.write("New content")

            # New file should not be skipped
            assert checker.should_skip(file_path) is False

    def test_should_skip_unchanged_file(self):
        """Test should_skip returns True for unchanged files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test_integrity.db"
            checker = SQLiteIntegrityChecker(db_path=db_path)

            file_path = f"{tmpdir}/test_file.txt"
            with open(file_path, "w") as f:
                f.write("Test content")

            # Mark as successfully processed
            checker.mark_success(file_path)

            # Now should_skip should return True
            assert checker.should_skip(file_path) is True

    def test_should_skip_modified_file(self):
        """Test should_skip returns False for modified files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test_integrity.db"
            checker = SQLiteIntegrityChecker(db_path=db_path)

            file_path = f"{tmpdir}/test_file.txt"
            with open(file_path, "w") as f:
                f.write("Original content")

            # Mark as successfully processed
            checker.mark_success(file_path)

            # Modify the file
            with open(file_path, "w") as f:
                f.write("Modified content")

            # Modified file should not be skipped
            assert checker.should_skip(file_path) is False

    def test_mark_success(self):
        """Test marking a file as successfully processed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test_integrity.db"
            checker = SQLiteIntegrityChecker(db_path=db_path)

            file_path = f"{tmpdir}/test.txt"
            with open(file_path, "w") as f:
                f.write("Content")

            checker.mark_success(file_path)

            # Verify it's stored
            processed = checker.get_processed_files()
            assert len(processed) == 1
            assert processed[0]["file_path"] == file_path

    def test_mark_failed(self):
        """Test marking a file as failed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test_integrity.db"
            checker = SQLiteIntegrityChecker(db_path=db_path)

            file_path = f"{tmpdir}/test.txt"
            with open(file_path, "w") as f:
                f.write("Content")

            checker.mark_failed(file_path, "Test error")

            # File should still be processable (not marked as success)
            assert checker.should_skip(file_path) is False

    def test_clear(self):
        """Test clearing all stored hashes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test_integrity.db"
            checker = SQLiteIntegrityChecker(db_path=db_path)

            file_path = f"{tmpdir}/test.txt"
            with open(file_path, "w") as f:
                f.write("Content")

            checker.mark_success(file_path)
            assert len(checker.get_processed_files()) == 1

            checker.clear()
            assert len(checker.get_processed_files()) == 0

    def test_get_processed_files(self):
        """Test getting list of processed files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test_integrity.db"
            checker = SQLiteIntegrityChecker(db_path=db_path)

            # Create multiple files
            for i in range(3):
                file_path = f"{tmpdir}/file{i}.txt"
                with open(file_path, "w") as f:
                    f.write(f"Content {i}")
                checker.mark_success(file_path)

            processed = checker.get_processed_files()
            assert len(processed) == 3
