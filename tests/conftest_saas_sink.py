"""Reusable SaaS-sink mock fixtures for WP09 (T041).

The canonical SaaS fanout boundary is
:func:`specify_cli.status.adapters.fire_saas_fanout`.  The
``mock_saas_sink`` fixture patches that boundary in *both* its
import-time location (``specify_cli.status.adapters.fire_saas_fanout``)
and in the public package location where ``coordination.outbound`` performs
its architecture-compliant lazy import
(``from specify_cli.status import fire_saas_fanout``).

A separate file (not directly auto-loaded by pytest) keeps this fixture
opt-in: tests that want to assert on outbound traffic do

    from tests.conftest_saas_sink import mock_saas_sink  # noqa: F401

inside their own conftest or import directly via ``pytest_plugins``.

Spec source: FR-022, NFR-009, SC-09.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest


class _RecordingSink:
    """Records every SaaS-fanout call so tests can assert on it.

    The instance exposes a ``calls`` list of ``(args, kwargs)`` tuples
    and convenience helpers (``call_count``, ``last_kwargs``) that keep
    test code compact.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append((args, kwargs))

    @property
    def call_count(self) -> int:
        return len(self.calls)

    @property
    def last_event(self) -> Any:
        if not self.calls:
            return None
        _, kwargs = self.calls[-1]
        return kwargs.get("event")

    @property
    def last_kwargs(self) -> dict[str, Any]:
        if not self.calls:
            return {}
        return self.calls[-1][1]


@pytest.fixture
def mock_saas_sink(monkeypatch: pytest.MonkeyPatch) -> Iterator[_RecordingSink]:
    """Patch ``fire_saas_fanout`` at every observable boundary.

    Yields a :class:`_RecordingSink` that captures every call.

    Boundaries patched:
      * ``specify_cli.status.adapters.fire_saas_fanout`` — the canonical
        import path. Existing callers that import the symbol at module
        load time see the patched version.
      * ``specify_cli.status.fire_saas_fanout`` — the public package boundary
        used by coordination code.
      * ``specify_cli.status.emit.fire_saas_fanout`` — emit.py imports
        the symbol at its module top, so monkeypatching the source alone
        does not catch its already-bound reference.

    The fixture is **safe to combine** with ``coordination.outbound.``
    ``queue_saas_emission`` because that helper performs a lazy
    ``from specify_cli.status import fire_saas_fanout`` inside
    ``_send_to_saas`` — so the patched package attribute is read
    fresh on every call.
    """
    sink = _RecordingSink()

    # Primary boundary
    monkeypatch.setattr(
        "specify_cli.status.adapters.fire_saas_fanout",
        sink,
    )
    monkeypatch.setattr(
        "specify_cli.status.fire_saas_fanout",
        sink,
    )

    # emit.py captured the symbol at import time; rebind there too so
    # existing emit-path tests work.
    try:
        import specify_cli.status.emit  # noqa: PLC0415

        if hasattr(specify_cli.status.emit, "fire_saas_fanout"):
            monkeypatch.setattr(
                "specify_cli.status.emit.fire_saas_fanout",
                sink,
            )
    except ImportError:
        # Defensive: tests that don't have emit on the import path can
        # still use the fixture; the adapter rebind alone covers the
        # outbound.py call path.
        pass

    yield sink
