"""Pytest configuration for all tests."""

import pytest


@pytest.fixture(autouse=True)
def reset_chroma():
    """Reset Chroma state between tests to avoid state conflicts."""
    import chromadb
    # Clear the SharedSystemClient state
    chromadb.api.shared_system_client.SharedSystemClient._identifier_to_system.clear()
    yield
    chromadb.api.shared_system_client.SharedSystemClient._identifier_to_system.clear()
