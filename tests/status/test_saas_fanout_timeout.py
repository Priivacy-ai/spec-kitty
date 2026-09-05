"""A hanging SaaS/lifecycle fan-out handler must never block canonical persistence.

Regression for the move-task sync-daemon hang: the status fan-out
(``fire_saas_fanout``) caught per-handler *exceptions* but nothing bounded a
handler that *hangs* (e.g. the sync daemon polling a stopped daemon with a large
offline-queue backlog). ``emit_status_transition`` documents "SaaS failures never
block canonical persistence" — that guarantee must cover hangs, not just raises.
"""

from __future__ import annotations

import logging
import threading
import time

import pytest

from specify_cli.status import adapters

# Pure-module threading behaviour (no subprocess/git/network); not `fast`
# because the orphan-thread teardown joins push some cases past sub-second.
pytestmark = [pytest.mark.unit]


@pytest.fixture(autouse=True)
def _clean_handlers() -> None:
    adapters.reset_handlers()
    yield
    adapters.reset_handlers()


def test_hanging_saas_handler_does_not_block_canonical_persistence(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("SPEC_KITTY_SAAS_FANOUT_TIMEOUT", "0.3")
    entered = threading.Event()
    release = threading.Event()

    def hanging_handler(**_kwargs: object) -> None:
        entered.set()
        # Simulate the daemon poll that never returns within the bound.
        release.wait(timeout=10)

    adapters.register_saas_fanout_handler(hanging_handler)

    start = time.monotonic()
    with caplog.at_level(logging.WARNING):
        adapters.fire_saas_fanout(
            wp_id="WP01", from_lane="in_progress", to_lane="for_review", force=False
        )
    elapsed = time.monotonic() - start

    # The canonical caller must return promptly despite the hanging handler.
    assert elapsed < 3.0, f"fan-out blocked for {elapsed:.1f}s on a hanging handler"
    assert entered.is_set(), "handler was expected to start"
    assert any(
        "timed out" in record.getMessage().lower() for record in caplog.records
    ), "a timeout warning should be logged"

    release.set()  # unblock the orphaned worker thread for clean teardown


def test_normal_saas_handler_still_runs_to_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_SAAS_FANOUT_TIMEOUT", "5")
    calls: list[str | None] = []

    def ok_handler(**kwargs: object) -> None:
        calls.append(kwargs.get("wp_id"))  # type: ignore[arg-type]

    adapters.register_saas_fanout_handler(ok_handler)
    adapters.fire_saas_fanout(
        wp_id="WP02", from_lane="planned", to_lane="claimed", force=False
    )
    assert calls == ["WP02"], "a well-behaved handler must run to completion synchronously"


def test_raising_saas_handler_is_still_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_SAAS_FANOUT_TIMEOUT", "5")

    def boom(**_kwargs: object) -> None:
        raise RuntimeError("handler blew up")

    adapters.register_saas_fanout_handler(boom)
    # Must not propagate — exceptions remain caught even with the bound in place.
    adapters.fire_saas_fanout(
        wp_id="WP03", from_lane="planned", to_lane="claimed", force=False
    )


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf", "Infinity"])
def test_nonfinite_timeout_falls_back_to_default_not_disabled(
    monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    # A non-finite value must NOT reach Thread.join() (nan raises immediately,
    # inf overflows) — that would silently disable the bound. It falls back to
    # the default, so a well-behaved handler still runs to completion.
    monkeypatch.setenv("SPEC_KITTY_SAAS_FANOUT_TIMEOUT", bad)
    assert adapters._saas_fanout_timeout_s() == adapters._DEFAULT_SAAS_FANOUT_TIMEOUT_S
    calls: list[object] = []
    adapters.register_saas_fanout_handler(lambda **k: calls.append(k.get("wp_id")))
    adapters.fire_saas_fanout(wp_id="WP09", from_lane="planned", to_lane="claimed")
    assert calls == ["WP09"]


def test_orphaned_handler_suppresses_an_overlapping_invocation(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("SPEC_KITTY_SAAS_FANOUT_TIMEOUT", "0.3")
    release = threading.Event()
    entry_count: list[int] = []
    lock = threading.Lock()

    def hanging_handler(**_kwargs: object) -> None:
        with lock:
            entry_count.append(1)
        release.wait(timeout=10)

    adapters.register_saas_fanout_handler(hanging_handler)

    # First call: spawns a worker that hangs past the 0.3s bound (orphaned).
    adapters.fire_saas_fanout(wp_id="WP10", from_lane="planned", to_lane="claimed")
    # Second call while the orphan is still running: must be skipped, NOT spawn
    # a second concurrent invocation of the same handler.
    with caplog.at_level(logging.WARNING):
        adapters.fire_saas_fanout(wp_id="WP11", from_lane="claimed", to_lane="in_progress")

    assert sum(entry_count) == 1, "the handler must not run a second, overlapping time"
    assert any("still in flight" in r.getMessage().lower() for r in caplog.records)

    release.set()  # let the orphan unwind and clear the in-flight key


def test_hanging_lifecycle_handler_does_not_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_SAAS_FANOUT_TIMEOUT", "0.3")
    release = threading.Event()

    def hanging_handler(**_kwargs: object) -> None:
        release.wait(timeout=10)

    adapters.register_lifecycle_saas_fanout_handler(hanging_handler)
    start = time.monotonic()
    adapters.fire_lifecycle_saas_fanout(wp_id="WP04")
    elapsed = time.monotonic() - start
    assert elapsed < 3.0, f"lifecycle fan-out blocked for {elapsed:.1f}s"
    release.set()
