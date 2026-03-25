"""Smoke tests to verify basic imports work correctly."""

import sys


def test_src_import():
    """Verify that src package can be imported."""
    import src
    assert src is not None


def test_main_import():
    """Verify that main module can be imported."""
    import main
    assert main is not None


def test_version():
    """Verify version is defined."""
    import main
    assert hasattr(main, "__version__")
    assert main.__version__ == "0.1.0"


def test_config_directory_exists():
    """Verify config directory exists."""
    import os

    assert os.path.exists("config")
    assert os.path.exists("config/settings.yaml")


def test_prompts_directory_exists():
    """Verify prompts directory exists."""
    import os

    assert os.path.exists("config/prompts")
    assert os.path.exists("config/prompts/medical_knowledge.txt")
