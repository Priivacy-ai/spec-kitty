"""Unit tests for specify_cli.invocation.adapters.

Covers the safe-degrade contract (unregistered → None), the register/
dispatch round-trip, idempotency by qualified name, exception suppression,
and the propagator safe-degrade behaviour when the seam is unregistered.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.invocation.adapters import (
    get_saas_client,
    register_saas_client_factory,
    register_sync_routing_resolver,
    reset_adapters,
    resolve_sync_routing,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# A dummy repo path — never touched on disk; only fed through the in-memory
# adapter registry (to mocked resolvers/factories). A rooted non-temp literal
# keeps it clear of the test-tree tmp-literal ratchet.
_DUMMY_PATH = Path("/repo")


@pytest.fixture(autouse=True)
def _clean_adapters() -> None:  # type: ignore[return]
    """Reset the adapter registry before and after every test."""
    reset_adapters()
    yield
    reset_adapters()


# ---------------------------------------------------------------------------
# resolve_sync_routing — safe-degrade when no resolver is registered
# ---------------------------------------------------------------------------


def test_resolve_sync_routing_returns_none_when_unregistered() -> None:
    """Dispatching with no registered resolver must return None."""
    result = resolve_sync_routing(_DUMMY_PATH)
    assert result is None


# ---------------------------------------------------------------------------
# get_saas_client — safe-degrade when no factory is registered
# ---------------------------------------------------------------------------


def test_get_saas_client_returns_none_when_unregistered() -> None:
    """Dispatching with no registered factory must return None."""
    result = get_saas_client(_DUMMY_PATH)
    assert result is None


# ---------------------------------------------------------------------------
# register_sync_routing_resolver — dispatch round-trip
# ---------------------------------------------------------------------------


def test_resolve_sync_routing_calls_registered_resolver() -> None:
    """After registration the resolver is called with the path and result is returned."""
    mock_resolver = MagicMock(return_value=True)
    register_sync_routing_resolver(mock_resolver)

    result = resolve_sync_routing(_DUMMY_PATH)

    mock_resolver.assert_called_once_with(_DUMMY_PATH)
    assert result is True


def test_resolve_sync_routing_returns_false_from_resolver() -> None:
    """A resolver returning False signals sync explicitly disabled."""
    register_sync_routing_resolver(lambda _path: False)

    result = resolve_sync_routing(_DUMMY_PATH)

    assert result is False


# ---------------------------------------------------------------------------
# register_saas_client_factory — dispatch round-trip
# ---------------------------------------------------------------------------


def test_get_saas_client_calls_registered_factory() -> None:
    """After registration the factory is called with the path and result is returned."""
    fake_client = MagicMock()
    mock_factory = MagicMock(return_value=fake_client)
    register_saas_client_factory(mock_factory)

    result = get_saas_client(_DUMMY_PATH)

    mock_factory.assert_called_once_with(_DUMMY_PATH)
    assert result is fake_client


# ---------------------------------------------------------------------------
# Idempotency — re-registering the same qualified name replaces the entry
# ---------------------------------------------------------------------------


def test_register_sync_routing_resolver_idempotent_by_qualname() -> None:
    """Re-registering a resolver with the same qualname replaces it."""
    call_log: list[str] = []

    def _resolver_v1(path: Path) -> bool | None:  # noqa: ARG001
        call_log.append("v1")
        return True

    def _resolver_v2(path: Path) -> bool | None:  # noqa: ARG001
        call_log.append("v2")
        return False

    # Rename v2 to share v1's qualified name, simulating a module reload
    _resolver_v2.__qualname__ = _resolver_v1.__qualname__
    _resolver_v2.__module__ = _resolver_v1.__module__

    register_sync_routing_resolver(_resolver_v1)
    register_sync_routing_resolver(_resolver_v2)

    resolve_sync_routing(_DUMMY_PATH)

    # Only v2 (the replacement) should have been called
    assert call_log == ["v2"]


def test_register_saas_client_factory_idempotent_by_qualname() -> None:
    """Re-registering a factory with the same qualname replaces it."""
    call_log: list[str] = []

    def _factory_v1(path: Path) -> object:  # noqa: ARG001
        call_log.append("v1")
        return object()

    def _factory_v2(path: Path) -> object:  # noqa: ARG001
        call_log.append("v2")
        return object()

    _factory_v2.__qualname__ = _factory_v1.__qualname__
    _factory_v2.__module__ = _factory_v1.__module__

    register_saas_client_factory(_factory_v1)
    register_saas_client_factory(_factory_v2)

    get_saas_client(_DUMMY_PATH)

    assert call_log == ["v2"]


# ---------------------------------------------------------------------------
# Exception suppression — a raising handler degrades to None
# ---------------------------------------------------------------------------


def test_resolve_sync_routing_returns_none_on_resolver_exception() -> None:
    """An exception in the resolver is caught; dispatch returns None."""

    def _exploding_resolver(_path: Path) -> bool | None:
        raise RuntimeError("boom")

    register_sync_routing_resolver(_exploding_resolver)

    result = resolve_sync_routing(_DUMMY_PATH)

    assert result is None


def test_get_saas_client_returns_none_on_factory_exception() -> None:
    """An exception in the factory is caught; dispatch returns None."""

    def _exploding_factory(_path: Path) -> object:
        raise RuntimeError("boom")

    register_saas_client_factory(_exploding_factory)

    result = get_saas_client(_DUMMY_PATH)

    assert result is None


# ---------------------------------------------------------------------------
# Propagator safe-degrade via the seam (integration-style unit test)
# ---------------------------------------------------------------------------


def test_propagator_safe_degrades_when_seam_unregistered(tmp_path: Path) -> None:
    """propagator._propagate_one must not raise when no adapters are registered.

    With no resolver or factory registered both dispatch calls return None,
    and _propagate_one should perform an early return at the sync-gate step
    (resolve_sync_routing returns None → not False → gate does not fire;
    _get_saas_client returns None → auth-gate fires → early return).
    This test imports propagator directly to verify the wiring without
    requiring the sync package.
    """
    from specify_cli.invocation import propagator
    from specify_cli.invocation.record import OpStartedEvent

    record = OpStartedEvent(
        invocation_id="01HXYZABCDEFGH1JK2MN3PQRST",
        profile_id="test-profile",
        action="implement",
        request_text="",
        actor="claude",
        mode_of_work="task_execution",
        governance_context_hash="abcdef0123456789",
        governance_context_available=False,
        started_at="2026-01-01T00:00:00Z",
    )

    # Must not raise; should silently return (sync-gate or auth-gate).
    propagator._propagate_one(record, tmp_path)


# ---------------------------------------------------------------------------
# Real registered factory contract tests (NFR-003 / Degradation Contract)
# These tests exercise the ACTUAL factory registered by specify_cli.sync —
# NOT a patched _get_saas_client — verifying the production registration.
# ---------------------------------------------------------------------------


@pytest.fixture()  # type: ignore[untyped-decorator]
def _registered_sync_handlers() -> Iterator[None]:
    """Reset adapters, register the real sync factories, then clean up.

    Uses SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 to prevent module-level
    auto-registration; we call register_default_handlers explicitly so the
    registry is always in a known state when the test runs.
    """
    reset_adapters()
    os.environ["SPEC_KITTY_SYNC_MINIMAL_IMPORT"] = "1"
    try:
        from specify_cli.sync import register_default_handlers

        register_default_handlers()
        yield
    finally:
        os.environ.pop("SPEC_KITTY_SYNC_MINIMAL_IMPORT", None)
        reset_adapters()


def test_registered_saas_factory_returns_none_when_not_authenticated(
    _registered_sync_handlers: None,
) -> None:
    """get_saas_client returns None when token_manager.is_authenticated is False.

    No client is constructed and no send attempt is made.
    """
    mock_tm = MagicMock()
    mock_tm.is_authenticated = False

    with patch("specify_cli.auth.get_token_manager", return_value=mock_tm):
        result = get_saas_client(_DUMMY_PATH)

    assert result is None
    mock_tm.get_current_session.assert_not_called()


def test_registered_saas_factory_returns_none_when_ws_client_not_connected(
    _registered_sync_handlers: None,
) -> None:
    """get_saas_client returns None when _ws_client exists but is not connected."""
    mock_ws = MagicMock()
    mock_ws.connected = False

    mock_tm = MagicMock()
    mock_tm.is_authenticated = True
    mock_tm.get_current_session.return_value = MagicMock()
    mock_tm._ws_client = mock_ws

    with patch("specify_cli.auth.get_token_manager", return_value=mock_tm):
        result = get_saas_client(_DUMMY_PATH)

    assert result is None


def test_registered_saas_factory_returns_existing_client_when_connected(
    _registered_sync_handlers: None,
) -> None:
    """get_saas_client returns the existing _ws_client when authenticated+connected.

    Must return the SAME connected instance, not a fresh disconnected one.
    A fresh WebSocketClient has .connected=False; send_event raises immediately.
    """
    mock_ws = MagicMock()
    mock_ws.connected = True

    mock_tm = MagicMock()
    mock_tm.is_authenticated = True
    mock_tm.get_current_session.return_value = MagicMock()
    mock_tm._ws_client = mock_ws

    with patch("specify_cli.auth.get_token_manager", return_value=mock_tm):
        result = get_saas_client(_DUMMY_PATH)

    assert result is mock_ws


def test_registered_routing_resolver_returns_none_for_non_project_path(
    _registered_sync_handlers: None,
) -> None:
    """resolve_sync_routing returns None cleanly for a non-project path.

    Previously the lambda called .effective_sync_enabled on a None result,
    raising AttributeError which was swallowed with exc_info=True — a spurious
    DEBUG traceback on every normal non-project path traversal.
    """
    with patch(
        "specify_cli.sync.routing.resolve_checkout_sync_routing",
        return_value=None,
    ):
        result = resolve_sync_routing(_DUMMY_PATH)

    assert result is None


def test_registered_routing_resolver_returns_flag_when_routing_present(
    _registered_sync_handlers: None,
) -> None:
    """resolve_sync_routing returns routing.effective_sync_enabled when routing resolves."""
    mock_routing = MagicMock()
    mock_routing.effective_sync_enabled = True

    with patch(
        "specify_cli.sync.routing.resolve_checkout_sync_routing",
        return_value=mock_routing,
    ):
        result = resolve_sync_routing(_DUMMY_PATH)

    assert result is True
