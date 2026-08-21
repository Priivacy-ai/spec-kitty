"""R2-T1 WP(a): explicit legacy sync-daemon retirement step.

``R2.md`` §3.2.2 requires one explicit, best-effort retirement step reachable
from a normal post-R2 CLI invocation that: detects a live daemon via the
existing ``owner.py`` mechanism, calls the existing no-drain
``stop_sync_daemon()`` path (reused unchanged), and reports the outcome. It
must never construct a new network primitive and must never "improve" the
no-drain shutdown on the way to deletion (§3.2.1).

This module tests ``specify_cli.sync.retirement.retire_legacy_sync_daemon``
against §4's negative/fault/race matrix rows N1-N3 (pure, no subprocess),
N4/N7/N8 (real subprocess, serial ``-n0`` per this repo's daemon-test
convention), plus a clean-absence baseline.

Row -> test map:
    N1  ownership-verification  -> test_alive_pid_with_wrong_identity_is_never_signaled
    N2  stale ownership record  -> test_stale_owner_record_is_cleared_without_contact
    N3  unverifiable process    -> test_malformed_owner_record_fails_closed
    N4  no-final-sync, explicit -> test_live_daemon_is_stopped_via_existing_no_drain_path
    N7  race/crash              -> test_sigkilled_daemon_converges_on_retry
    N8  race, concurrent stop   -> test_concurrent_retirement_is_idempotent
    --  baseline                -> test_absent_owner_record_is_a_clean_noop
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from tests.sync._daemon_harness import DaemonHarness, find_free_port_in_range

pytestmark = [pytest.mark.integration]

_TOKEN = "r2t1-retirement-fixture-token"  # noqa: S105 - fixture value only


@pytest.fixture(autouse=True)
def _scoped_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate ``SPEC_KITTY_HOME`` so ``owner.json`` / the daemon state file
    land under ``tmp_path`` for this test only (matches
    ``get_runtime_root()``'s resolution order: ``SPEC_KITTY_HOME`` wins).
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def _build_record(**overrides: Any) -> Any:
    from specify_cli.sync.owner import DaemonOwnerRecord

    defaults: dict[str, Any] = {
        "pid": os.getpid(),
        "port": 9410,
        "token": _TOKEN,
        "package_version": "3.2.0",
        "executable_path": sys.executable,
        "source_checkout_path": str(Path(__file__).resolve().parents[2]),
        "server_url": "https://spec-kitty-dev.fly.dev",
        "auth_principal": "tester@example.com",
        "auth_team": "t-private",
        "auth_scope": "https://spec-kitty-dev.fly.dev|tester@example.com|t-private",
        "queue_db_path": str(Path.home() / ".spec-kitty" / "queues" / "queue-aaaaaaaa.db"),
        "started_at": "2026-05-17T16:42:00+00:00",
    }
    defaults.update(overrides)
    return DaemonOwnerRecord(**defaults)


def _owner_json_path(scoped_home: Path) -> Path:
    return scoped_home / "sync" / "daemon" / "owner.json"


# ---------------------------------------------------------------------------
# N1 - ownership-verification: alive PID, wrong identity
# ---------------------------------------------------------------------------


def test_alive_pid_with_wrong_identity_is_never_signaled(_scoped_home: Path) -> None:
    from specify_cli.sync.owner import write_owner_record
    from specify_cli.sync.retirement import retire_legacy_sync_daemon

    impostor = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        # Give the impostor a moment to actually be alive/scheduled.
        time.sleep(0.2)
        write_owner_record(_build_record(pid=impostor.pid, port=9411))

        outcome = retire_legacy_sync_daemon()

        assert outcome.status == "unverified_ownership"
        assert str(impostor.pid) in outcome.detail or "spawn signature" in outcome.detail
        # The impostor must still be alive: no signal was ever sent to it.
        assert impostor.poll() is None
        # The owner record is left in place -- fail closed, not silently cleared.
        assert _owner_json_path(_scoped_home).exists()
    finally:
        impostor.terminate()
        impostor.wait(timeout=5.0)


# ---------------------------------------------------------------------------
# N2 - stale ownership record (dead PID)
# ---------------------------------------------------------------------------


def test_stale_owner_record_is_cleared_without_contact(_scoped_home: Path) -> None:
    from specify_cli.sync.owner import write_owner_record
    from specify_cli.sync.retirement import retire_legacy_sync_daemon

    finished = subprocess.Popen(
        [sys.executable, "-c", "pass"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    finished.wait(timeout=5.0)
    dead_pid = finished.pid

    write_owner_record(_build_record(pid=dead_pid, port=9412))

    outcome = retire_legacy_sync_daemon()

    assert outcome.status == "cleared_stale"
    assert not _owner_json_path(_scoped_home).exists()


# ---------------------------------------------------------------------------
# N3 - unverifiable process (malformed owner.json)
# ---------------------------------------------------------------------------


def test_malformed_owner_record_fails_closed(_scoped_home: Path) -> None:
    from specify_cli.sync.retirement import retire_legacy_sync_daemon

    owner_path = _owner_json_path(_scoped_home)
    owner_path.parent.mkdir(parents=True, exist_ok=True)
    owner_path.write_text("{not valid json", encoding="utf-8")

    outcome = retire_legacy_sync_daemon()

    assert outcome.status == "unverifiable_owner_record"
    # Fail closed: the unreadable file is left exactly as found, never
    # deleted and never treated as "no daemon".
    assert owner_path.read_text(encoding="utf-8") == "{not valid json"


# ---------------------------------------------------------------------------
# Baseline - no owner record at all
# ---------------------------------------------------------------------------


def test_absent_owner_record_is_a_clean_noop(_scoped_home: Path) -> None:
    from specify_cli.sync.retirement import retire_legacy_sync_daemon

    assert not _owner_json_path(_scoped_home).exists()

    outcome = retire_legacy_sync_daemon()

    assert outcome.status == "no_daemon"


# ---------------------------------------------------------------------------
# N4 - real daemon, explicit stop, existing no-drain path reused unchanged
# ---------------------------------------------------------------------------


def test_live_daemon_is_stopped_via_existing_no_drain_path(
    _scoped_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from specify_cli.sync import daemon as daemon_module
    from specify_cli.sync.retirement import retire_legacy_sync_daemon

    # ``_daemon_state_file()`` resolves to ``<SPEC_KITTY_HOME>/sync-daemon`` on
    # POSIX (``daemon._daemon_root()``); point the harness there so
    # ``stop_sync_daemon()`` -- the existing no-drain path this module reuses
    # unchanged -- finds it, matching what the real spawn path
    # (``ensure_sync_daemon_running`` -> ``_write_daemon_file``) always writes
    # alongside ``owner.json`` in production.
    #
    # Pinned explicitly via ``monkeypatch.setattr`` rather than left to
    # ``SPEC_KITTY_HOME`` resolution alone: ``DAEMON_STATE_FILE`` is served by
    # ``daemon.__getattr__`` (never a real module global) until some test
    # patches it, and ``monkeypatch``'s teardown then "restores" that
    # resolved-at-patch-time ``Path`` as a REAL, permanent module attribute --
    # which freezes ``_resolve_lazy_path``'s override branch for the rest of
    # the pytest process, shadowing every later test's own
    # ``SPEC_KITTY_HOME``. Reproduced directly: this test passes alone but
    # failed after ``test_daemon_orphan_classification.py`` ran first in the
    # same ``-n0`` process, for exactly this reason. Pinning here (the same
    # pattern ``test_daemon_self_retirement.py`` and
    # ``test_daemon_orphan_classification.py`` itself already use) makes this
    # test immune to that ordering, rather than relying on being scheduled
    # first.
    state_file = _scoped_home / "sync-daemon"
    monkeypatch.setattr(daemon_module, "DAEMON_STATE_FILE", state_file)
    harness = DaemonHarness(state_file)
    port = find_free_port_in_range(9400, 9425)
    try:
        proc = harness.spawn_daemon(port, _TOKEN, home=str(_scoped_home))
        harness.write_state_file(
            f"http://127.0.0.1:{port}", port, _TOKEN, proc.pid
        )

        outcome = retire_legacy_sync_daemon()

        assert outcome.status == "stopped"
        proc.wait(timeout=5.0)
        assert proc.poll() is not None, "daemon process must have exited"
        assert not _owner_json_path(_scoped_home).exists()
    finally:
        harness.shutdown()


# ---------------------------------------------------------------------------
# N7 - race/crash: SIGKILL bypassing clean shutdown entirely
# ---------------------------------------------------------------------------


def test_sigkilled_daemon_converges_on_retry(tmp_path: Path, _scoped_home: Path) -> None:
    from specify_cli.sync.retirement import retire_legacy_sync_daemon

    harness = DaemonHarness(tmp_path / "sync-daemon")
    port = find_free_port_in_range(9400, 9425)
    try:
        proc = harness.spawn_daemon(port, _TOKEN, home=str(_scoped_home))
        proc.kill()
        proc.wait(timeout=5.0)

        # The daemon never ran its own signal handler (SIGKILL cannot be
        # caught) so owner.json is still on disk, naming a now-dead PID.
        assert _owner_json_path(_scoped_home).exists()

        outcome = retire_legacy_sync_daemon()

        assert outcome.status == "cleared_stale"
        assert not _owner_json_path(_scoped_home).exists()

        # Idempotent: a second call converges cleanly on the now-clean state.
        second = retire_legacy_sync_daemon()
        assert second.status == "no_daemon"
    finally:
        harness.shutdown()


# ---------------------------------------------------------------------------
# N8 - race, concurrent stop
# ---------------------------------------------------------------------------


def test_concurrent_retirement_is_idempotent(
    _scoped_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from specify_cli.sync import daemon as daemon_module
    from specify_cli.sync.retirement import retire_legacy_sync_daemon

    # See the matching comment in
    # ``test_live_daemon_is_stopped_via_existing_no_drain_path`` for why this
    # pin is required, not merely defensive.
    state_file = _scoped_home / "sync-daemon"
    monkeypatch.setattr(daemon_module, "DAEMON_STATE_FILE", state_file)
    harness = DaemonHarness(state_file)
    port = find_free_port_in_range(9400, 9425)
    try:
        proc = harness.spawn_daemon(port, _TOKEN, home=str(_scoped_home))
        harness.write_state_file(
            f"http://127.0.0.1:{port}", port, _TOKEN, proc.pid
        )

        results: list[Any] = [None, None]

        def _call(index: int) -> None:
            results[index] = retire_legacy_sync_daemon()

        t1 = threading.Thread(target=_call, args=(0,))
        t2 = threading.Thread(target=_call, args=(1,))
        t1.start()
        t2.start()
        t1.join(timeout=10.0)
        t2.join(timeout=10.0)

        assert not t1.is_alive()
        assert not t2.is_alive()
        assert results[0] is not None
        assert results[1] is not None

        statuses = {results[0].status, results[1].status}
        # Exactly one call actually stops the daemon; the other observes
        # either a benign "already gone" state or, on a tight race, also
        # wins a legitimate stop -- what must never happen is a raised
        # exception or a double-kill error, which the two ``.join()``
        # calls above (no exception propagation) already rule out.
        assert statuses <= {"stopped", "already_stopped", "no_daemon"}

        proc.wait(timeout=5.0)
        assert proc.poll() is not None
        assert not _owner_json_path(_scoped_home).exists()
    finally:
        harness.shutdown()
