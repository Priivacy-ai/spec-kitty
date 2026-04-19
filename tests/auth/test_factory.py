"""Tests for the ``get_token_manager()`` factory (feature 080, WP01 T001)."""

from __future__ import annotations

import concurrent.futures
from unittest.mock import Mock, patch

import pytest

from specify_cli.auth import TokenManager, get_token_manager, reset_token_manager


@pytest.fixture(autouse=True)
def _reset_tm():
    reset_token_manager()
    yield
    reset_token_manager()


def _mock_storage() -> Mock:
    storage = Mock()
    storage.read.return_value = None
    storage.write = Mock(return_value=None)
    storage.delete = Mock(return_value=None)
    storage.backend_name = "file"
    return storage


def test_factory_returns_token_manager_instance():
    storage = _mock_storage()
    with patch(
        "specify_cli.auth.SecureStorage.from_environment",
        return_value=storage,
    ) as mock_from_environment:
        tm = get_token_manager()
    assert isinstance(tm, TokenManager)
    mock_from_environment.assert_called_once()
    assert tm._storage is storage


def test_factory_returns_same_instance_on_repeat_calls():
    storage = _mock_storage()
    with patch(
        "specify_cli.auth.SecureStorage.from_environment",
        return_value=storage,
    ) as mock_from_environment:
        tm1 = get_token_manager()
        tm2 = get_token_manager()
    assert tm1 is tm2
    mock_from_environment.assert_called_once()


def test_reset_token_manager_creates_fresh_instance():
    with patch(
        "specify_cli.auth.SecureStorage.from_environment",
        return_value=_mock_storage(),
    ):
        tm1 = get_token_manager()
    reset_token_manager()
    with patch(
        "specify_cli.auth.SecureStorage.from_environment",
        return_value=_mock_storage(),
    ):
        tm2 = get_token_manager()
    assert tm1 is not tm2


def test_factory_uses_secure_storage_from_environment():
    storage = _mock_storage()
    with patch(
        "specify_cli.auth.SecureStorage.from_environment",
        return_value=storage,
    ) as mock_from_environment:
        tm = get_token_manager()
    assert tm is not None
    mock_from_environment.assert_called_once()
    assert tm._storage is storage


def test_factory_is_thread_safe():
    """Concurrent first-call must still return a single shared instance."""
    storage = _mock_storage()
    with patch(
        "specify_cli.auth.SecureStorage.from_environment",
        return_value=storage,
    ) as mock_from_environment:

        def call() -> TokenManager:
            return get_token_manager()

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
            results = list(ex.map(lambda _: call(), range(64)))

    first = results[0]
    assert all(r is first for r in results)
    mock_from_environment.assert_called_once()
