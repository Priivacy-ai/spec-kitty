"""Shared fixtures for the ``tests/auth/`` suite (feature 080, WP01)."""

from __future__ import annotations

import pytest

from specify_cli.auth import reset_token_manager


@pytest.fixture(autouse=True)
def _reset_tm():
    """Reset the process-wide TokenManager between auth tests.

    Guarantees no state leakage from one test to another.
    """
    reset_token_manager()
    yield
    reset_token_manager()
