"""Pytest configuration for events tests."""
import pytest


@pytest.fixture(autouse=True)
def patch_home(tmp_path, monkeypatch):
    """Patch HOME environment variable for all tests in this directory.

    This ensures LamportClock writes to a temporary directory instead of
    the real HOME directory, making tests hermetic and safe for restricted
    environments.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
