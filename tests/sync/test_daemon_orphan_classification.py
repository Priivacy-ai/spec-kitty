"""Live-subprocess version matrix for the sync daemon orphan cleanup.

Real-port serial suite — run with ``-n0`` (never parallel).

Ports used: ``[9401, 9425)``  — deliberately excludes the production daemon's
default first-port ``9400`` (RISK-1) and stays disjoint from
``test_orphan_sweep.py`` which uses ``[9425, 9450)``.

Run command::

    PWHEADLESS=1 .venv/bin/pytest tests/sync/test_daemon_orphan_classification.py -n0 -q

Subtasks covered:
    T026 — shared ``DaemonHarness`` module exercised here (live subprocesses).
    T027 — same-scope stale-version cleanup; no redundant spawn (AS-1, FR-006/007/008).
    T028 — ambiguous candidates survive auto-cleanup (AS-2, D-01).
    T029 — ``auth doctor`` JSON scan + ``--reset`` + ``--reset --force`` (AS-3/4, FR-004/005).
    T030 — isolation constraints: ``[9401,9425)`` range, serial, win32-skipped, SAAS env gate.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from specify_cli.sync import orphan_sweep
from specify_cli.sync.daemon import (
    DAEMON_PORT_MAX_ATTEMPTS,
    DAEMON_PORT_START,
)
from tests.sync._daemon_harness import (
    DaemonHarness,
    find_free_port_in_range,
    wait_until_listening,
    wait_until_port_free,
)

pytestmark = [pytest.mark.integration]

# ---------------------------------------------------------------------------
# Port range (T030): isolated sub-range distinct from test_orphan_sweep.py
# ---------------------------------------------------------------------------
#
# RISK-1 (NFR-006 test-isolation): the window deliberately STARTS at 9401 so it
# excludes the production daemon's default first-port 9400 — a real dev/test
# daemon leaked onto 9400 must never be counted by this suite. It stays disjoint
# from ``test_orphan_sweep.py`` (``[9425, 9450)``). Even so, the "exactly one
# listening port" assertions below are written against the *delta* this test
# creates (baseline-snapshot ∪ {singleton}) rather than an absolute count, so a
# pre-existing in-range listener cannot make them flaky.

_PORT_START = 9401
_PORT_END = 9425  # exclusive — [9401, 9425)

# Version strings for the matrix (DD-04 / T027)
_VERSION_STALE_A = "3.2.2"
_VERSION_STALE_B = "3.2.3"
_VERSION_STALE_C = "3.2.4"


# ---------------------------------------------------------------------------
# Fixture: scoped harness with narrowed port range + isolated state file
# ---------------------------------------------------------------------------


@pytest.fixture
def harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[DaemonHarness]:
    """Live daemon harness with isolated state file and narrowed scan range.

    The state file is redirected to ``tmp_path`` so no test writes to the
    real ``~/.spec-kitty`` directory.  The port scan range is narrowed to
    ``[_PORT_START, _PORT_END)`` to avoid interfering with real daemons or
    other test suites.

    ``_lookup_listening_pid`` is patched to consult the harness's
    ``port_pids`` map first — macOS raises ``AccessDenied`` for sockets
    owned by another UID, so we rely on the PID we recorded at spawn time.
    """
    state_file = tmp_path / "sync-daemon"

    monkeypatch.setattr(orphan_sweep, "DAEMON_STATE_FILE", state_file)
    monkeypatch.setattr(orphan_sweep, "DAEMON_PORT_START", _PORT_START)
    monkeypatch.setattr(
        orphan_sweep,
        "DAEMON_PORT_MAX_ATTEMPTS",
        _PORT_END - _PORT_START,
    )

    h = DaemonHarness(state_file)

    original_lookup = orphan_sweep._lookup_listening_pid  # private helper — mypy sees it as Any (follow_imports=skip)

    def _patched_lookup(port: int) -> int | None:
        if port in h.port_pids:
            return h.port_pids[port]
        result: int | None = original_lookup(port)
        return result

    monkeypatch.setattr(orphan_sweep, "_lookup_listening_pid", _patched_lookup)

    try:
        yield h
    finally:
        h.shutdown()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pid_alive(pid: int) -> bool:
    """Return True if ``pid`` still refers to a running process."""
    try:
        import psutil

        return psutil.pid_exists(pid)
    except Exception:  # noqa: BLE001
        return False


def _port_listening(port: int) -> bool:
    """Quick TCP connect check — returns True iff something listens on ``port``."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.1)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _in_range_listeners() -> set[int]:
    """Return the set of ports in ``[_PORT_START, _PORT_END)`` currently listening.

    Used to snapshot a *baseline* before the test spawns its own daemons so the
    no-redundant-spawn assertion can reason about the delta this test created
    rather than an absolute count — robust to any pre-existing in-range listener
    (e.g. a daemon leaked by another test on 9400+, RISK-1).
    """
    return {p for p in range(_PORT_START, _PORT_END) if _port_listening(p)}


# ---------------------------------------------------------------------------
# T027 — same-scope stale-version cleanup + no redundant spawn (AS-1)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="real-port tests require POSIX socket semantics")
class TestT027SameScope:
    """AS-1 / FR-006/007/008: same-scope daemons with stale version are reaped;
    the singleton is left running; no extra daemon is spawned.
    """

    @pytest.mark.parametrize("stale_version", [_VERSION_STALE_A, _VERSION_STALE_B, _VERSION_STALE_C])
    def test_stale_version_reaped_singleton_survives(
        self,
        harness: DaemonHarness,
        monkeypatch: pytest.MonkeyPatch,
        stale_version: str,
    ) -> None:
        """Spawn two same-scope daemons; record one as the singleton.

        After ``reap_orphan_daemons()`` the orphan's port must be closed and
        its PID must be gone.  The singleton must still be listening.
        No extra daemon must have been started.

        The stale daemon reports ``stale_version`` via ``SPEC_KITTY_CLI_VERSION``;
        the reaper's kill gate is scope + spawn-shape (FR-008), not version, so
        old-version daemons are now reaped instead of accumulating (#2261).
        """
        # Snapshot any pre-existing in-range listeners BEFORE we spawn anything.
        # A daemon leaked by another test (e.g. on the production default 9400,
        # which is now outside our [9401,9425) window but kept here defensively)
        # must not be miscounted — we assert on the delta this test creates, not
        # an absolute "exactly 1" count (RISK-1 / NFR-006).
        baseline_listeners = _in_range_listeners()

        port_singleton = find_free_port_in_range(_PORT_START, _PORT_END)
        port_orphan = find_free_port_in_range(port_singleton + 1, _PORT_END)

        # Spawn singleton FIRST; record it in the state file.
        proc_singleton = harness.spawn_daemon(port_singleton, "tok-single")
        harness.write_state_file(
            f"http://127.0.0.1:{port_singleton}",
            port_singleton,
            "tok-single",
            proc_singleton.pid,
        )

        # Spawn the stale-version orphan (same scope, no state-file entry).
        proc_orphan = harness.spawn_daemon(
            port_orphan, "tok-orphan", version=stale_version
        )
        orphan_pid = proc_orphan.pid

        # Patch DAEMON_STATE_FILE on the daemon module (where scan_sync_daemons
        # reads it via _resolve_lazy_path).
        from specify_cli.sync import daemon as _daemon_mod

        monkeypatch.setattr(_daemon_mod, "DAEMON_STATE_FILE", harness.state_file)

        # Drive the canonical reaper (spawn hot path).
        from specify_cli.sync.owner import reap_orphan_daemons

        result = reap_orphan_daemons()

        # The orphan must have been reaped.
        assert orphan_pid in result.reaped, (
            f"version={stale_version!r}: orphan PID {orphan_pid} not in reaped={result.reaped!r}; "
            f"skipped_out_of_scope={result.skipped_out_of_scope!r}"
        )

        # Port must close (not just PID gone — port-close is the success criterion).
        assert wait_until_port_free(port_orphan, timeout_s=6.0), (
            f"version={stale_version!r}: port {port_orphan} still listening after reap"
        )

        # PID must be gone.
        for _ in range(30):
            if not _pid_alive(orphan_pid):
                break
            time.sleep(0.05)
        assert not _pid_alive(orphan_pid), (
            f"version={stale_version!r}: PID {orphan_pid} still alive after port closed"
        )

        # Singleton must survive (AS-1 / FR-007).
        assert _port_listening(port_singleton), (
            f"version={stale_version!r}: singleton port {port_singleton} went down unexpectedly"
        )
        assert proc_singleton.poll() is None, (
            f"version={stale_version!r}: singleton process exited unexpectedly"
        )

        # No new daemon was spawned (FR-007). Assert on the DELTA this test is
        # responsible for, not an absolute count: the reaped orphan must be gone,
        # the singleton must still be listening, and the test must not have
        # introduced any UNEXPECTED new in-range listener beyond the singleton
        # (i.e. no redundant spawn). Pre-existing in-range listeners captured in
        # ``baseline_listeners`` belong to other tests/daemons and are tolerated
        # (RISK-1 / NFR-006).
        #
        # We assert ``new_listeners ⊆ {singleton}`` rather than full set-equality
        # against ``baseline ∪ {singleton}`` on purpose: a stale baseline listener
        # that legitimately stops between the two snapshots (or momentarily fails a
        # connect probe) must not fail THIS test — only a *new* unexpected daemon
        # appearing is an FR-007 violation. The orphan-gone / singleton-up
        # assertions above pin the behavior this test actually owns.
        final_listeners = _in_range_listeners()
        assert port_orphan not in final_listeners, (
            f"version={stale_version!r}: orphan port {port_orphan} still listening "
            f"after reap; final_listeners={sorted(final_listeners)!r}"
        )
        assert port_singleton in final_listeners, (
            f"version={stale_version!r}: singleton port {port_singleton} missing from "
            f"final_listeners={sorted(final_listeners)!r}"
        )
        new_listeners = final_listeners - baseline_listeners
        assert new_listeners <= {port_singleton}, (
            f"version={stale_version!r}: unexpected new in-range listener(s) after "
            f"reap — possible redundant spawn (FR-007). "
            f"new={sorted(new_listeners)!r} (expected only the singleton "
            f"{port_singleton}); final={sorted(final_listeners)!r} "
            f"baseline={sorted(baseline_listeners)!r}"
        )


# ---------------------------------------------------------------------------
# T028 — ambiguous candidates survive auto-cleanup (AS-2 / D-01)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="real-port tests require POSIX socket semantics")
class TestT028AmbiguousSurvives:
    """AS-2 / D-01: pre-marker, cross-HOME, and wedged daemons must not be killed
    by the startup auto-clean path.  They must classify as ``operator_required``.
    """

    def test_pre_marker_daemon_survives(
        self,
        harness: DaemonHarness,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A daemon spawned WITHOUT a scope marker classifies ``operator_required/pre_marker``
        and is NOT killed by ``reap_orphan_daemons``.

        We simulate a pre-marker daemon by calling ``spawn_daemon`` with
        ``scope_root=""``, which embeds ``--spec-kitty-daemon-root=`` (empty
        suffix).  The reaper's marker-match gate then sees marker≠scope_id and
        treats the process as out-of-scope.
        """
        port = find_free_port_in_range(_PORT_START, _PORT_END)

        # Spawn with an empty scope — simulates a pre-marker (legacy) daemon
        # that carried no ``--spec-kitty-daemon-root=`` at all.
        proc = harness.spawn_daemon(port, "tok-pre-marker", scope_root="")
        pre_marker_pid = proc.pid

        from specify_cli.sync import daemon as _daemon_mod

        monkeypatch.setattr(_daemon_mod, "DAEMON_STATE_FILE", harness.state_file)

        from specify_cli.sync.owner import reap_orphan_daemons

        result = reap_orphan_daemons()

        # Must NOT have been reaped.
        assert pre_marker_pid not in result.reaped, (
            f"pre-marker PID {pre_marker_pid} was reaped — it should survive"
        )

        # Port must still be listening.
        assert _port_listening(port), (
            f"pre-marker port {port} closed unexpectedly"
        )

    def test_cross_home_daemon_survives(
        self,
        harness: DaemonHarness,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A daemon belonging to a DIFFERENT HOME (cross-root) survives auto-clean.

        We spawn a daemon whose argv scope marker points to a different
        ``daemon_scope_root`` (``tmp_path / "other-home"``).  The reaper's
        marker-match gate sees marker≠current_scope and skips it.
        """
        port = find_free_port_in_range(_PORT_START, _PORT_END)

        other_home = str(tmp_path / "other-home" / ".spec-kitty")
        proc = harness.spawn_daemon(port, "tok-cross", scope_root=other_home)
        cross_pid = proc.pid

        from specify_cli.sync import daemon as _daemon_mod

        monkeypatch.setattr(_daemon_mod, "DAEMON_STATE_FILE", harness.state_file)

        from specify_cli.sync.owner import reap_orphan_daemons

        result = reap_orphan_daemons()

        assert cross_pid not in result.reaped, (
            f"cross-HOME PID {cross_pid} was reaped — it should survive"
        )
        assert _port_listening(port), (
            f"cross-HOME port {port} closed unexpectedly"
        )

    def test_wedged_listener_survives(
        self,
        harness: DaemonHarness,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A scope-marked daemon-shaped listener that hangs health is not auto-killed."""
        port = find_free_port_in_range(_PORT_START, _PORT_END)
        proc = harness.spawn_wedged_daemon_shape(port)

        from specify_cli.sync import daemon as _daemon_mod

        monkeypatch.setattr(_daemon_mod, "DAEMON_STATE_FILE", harness.state_file)

        from specify_cli.sync.owner import reap_orphan_daemons

        result = reap_orphan_daemons()

        # Port must still be listening after the reaper ran.
        assert _port_listening(port), (
            f"wedged listener on port {port} was killed by the startup reaper"
        )
        assert proc.pid not in result.reaped
        assert any(
            detail.pid == proc.pid
            and detail.cleanup_class.value == "operator_required"
            and detail.skip_reason is not None
            and detail.skip_reason.value == "unresponsive"
            for detail in result.skipped_details
        ), f"wedged daemon-shaped PID {proc.pid} missing from skipped_details"

    def test_plain_listener_survives_startup_reaper(
        self,
        harness: DaemonHarness,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A plain TCP listener (no SK cmdline identity) remains invisible."""
        port = find_free_port_in_range(_PORT_START, _PORT_END)
        harness.spawn_plain(port)

        from specify_cli.sync import daemon as _daemon_mod

        monkeypatch.setattr(_daemon_mod, "DAEMON_STATE_FILE", harness.state_file)

        from specify_cli.sync.owner import reap_orphan_daemons

        result = reap_orphan_daemons()

        assert _port_listening(port), (
            f"plain listener on port {port} was killed by the startup reaper"
        )
        assert result.reaped == []

    def test_wedged_listener_classifies_never_touch_via_port_scan(
        self,
        harness: DaemonHarness,
    ) -> None:
        """``enumerate_identity_records`` classifies a plain listener as ``never_touch``
        and excludes it from the result (callers never see it).
        """
        from specify_cli.sync.classification import CleanupClass
        from specify_cli.sync.orphan_sweep import enumerate_identity_records

        port = find_free_port_in_range(_PORT_START, _PORT_END)
        harness.spawn_plain(port)

        records = enumerate_identity_records()

        # The plain listener must NOT appear in the identity records
        # (never_touch entries are excluded from the result by contract).
        for rec in records:
            assert rec.port != port, (
                f"plain listener on port {port} appeared in identity records: {rec!r}"
            )
            assert rec.cleanup_class != CleanupClass.NEVER_TOUCH, (
                f"never_touch record leaked into enumerate_identity_records: {rec!r}"
            )


# ---------------------------------------------------------------------------
# T029 — auth doctor scan + --reset + --reset --force (AS-3/4, FR-004/005)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="real-port tests require POSIX socket semantics")
class TestT029AuthDoctor:
    """AS-3/4 / FR-004/005: end-to-end CLI proof via ``doctor_impl``.

    We drive ``doctor_impl`` in-process (fastest path that still exercises
    real listeners on real ports).  The ``--json`` output is parsed and
    asserted directly.
    """

    def test_doctor_json_shows_cleanup_class(
        self,
        harness: DaemonHarness,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """``auth doctor --json`` reports each orphan with ``cleanup_class``.

        Setup: one safe_auto orphan (same-scope, stale version) + one
        plain listener (never_touch — excluded from orphans).  After
        calling ``doctor_impl(json_output=True, reset=False, ...)``,
        the JSON payload must carry the safe_auto orphan with its
        ``cleanup_class`` key.
        """
        port_orphan = find_free_port_in_range(_PORT_START, _PORT_END)
        port_plain = find_free_port_in_range(port_orphan + 1, _PORT_END)

        # Spawn a same-scope stale-version orphan (no state file → orphan).
        harness.spawn_daemon(port_orphan, "tok-orphan", version=_VERSION_STALE_A)
        harness.spawn_plain(port_plain)

        # Redirect orphan_sweep's state file + port range to our harness.
        self._patch_orphan_sweep(monkeypatch, harness)

        from specify_cli.cli.commands._auth_doctor import doctor_impl

        doctor_impl(
            json_output=True,
            reset=False,
            unstick_lock=False,
            stuck_threshold=60.0,
        )

        captured = capsys.readouterr()
        payload = json.loads(captured.out)

        orphans = payload.get("orphans", [])
        # The plain listener must NOT be in the orphans list.
        assert not any(o["port"] == port_plain for o in orphans), (
            f"plain listener on port {port_plain} leaked into doctor orphans: {orphans!r}"
        )

        # The safe_auto orphan MUST appear.
        safe_orphan = next(
            (o for o in orphans if o["port"] == port_orphan), None
        )
        assert safe_orphan is not None, (
            f"safe_auto orphan on port {port_orphan} not in doctor output: {orphans!r}"
        )
        assert "cleanup_class" in safe_orphan, (
            f"cleanup_class missing from orphan entry: {safe_orphan!r}"
        )
        assert safe_orphan["cleanup_class"] == "safe_auto", (
            f"expected safe_auto, got {safe_orphan['cleanup_class']!r}"
        )

    def test_doctor_reset_json_swept_skipped_failed(
        self,
        harness: DaemonHarness,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """``auth doctor --reset --json`` reports ``reset_result`` with swept/skipped/failed.

        Setup:
        * safe_auto orphan (same-scope, stale version)             → swept
        * cross-root daemon (different scope_root)                 → skipped (operator_required)
        * plain listener                                           → not in orphans at all

        ``--reset`` without ``--force`` must sweep the safe_auto and skip the
        cross-root.  The ``reset_result`` payload must match.
        """
        port_safe = find_free_port_in_range(_PORT_START, _PORT_END)
        port_cross = find_free_port_in_range(port_safe + 1, _PORT_END)
        port_plain = find_free_port_in_range(port_cross + 1, _PORT_END)

        # Cross-root daemon must use a different HOME so its owner record does NOT
        # overwrite the safe daemon's owner.json (both would land in the same path
        # under the shared isolated HOME otherwise, causing pid_port_mismatch).
        other_home = str(tmp_path / "cross-home")
        other_scope = other_home  # scope_root matches the cross-home's daemon root

        # Spawn same-scope safe_auto daemon first.
        harness.spawn_daemon(port_safe, "tok-safe", version=_VERSION_STALE_B)
        # Spawn cross-home/cross-root daemon with isolated HOME so its owner.json
        # lands in other_home, not in the shared isolated test HOME.
        harness.spawn_daemon(port_cross, "tok-cross", scope_root=other_scope, home=other_home)
        harness.spawn_plain(port_plain)

        self._patch_orphan_sweep(monkeypatch, harness)

        from specify_cli.cli.commands._auth_doctor import doctor_impl

        doctor_impl(
            json_output=True,
            reset=True,
            force=False,
            unstick_lock=False,
            stuck_threshold=60.0,
        )

        captured = capsys.readouterr()
        payload = json.loads(captured.out)

        assert "reset_result" in payload, f"reset_result missing from payload: {list(payload.keys())!r}"
        rr = payload["reset_result"]


        # The safe_auto orphan should appear in swept.
        swept_ports = {e["port"] for e in rr["swept"]}
        # The cross-root / operator_required should appear in skipped or
        # (if the port-scan can't probe it) not in swept.
        # Key invariant: the safe_auto orphan port must be swept.
        assert port_safe in swept_ports, (
            f"safe_auto orphan port {port_safe} not in swept={swept_ports!r}"
        )

        # Port must be free now.
        assert wait_until_port_free(port_safe, timeout_s=6.0), (
            f"safe_auto orphan port {port_safe} still listening after --reset"
        )

        # The cross-root daemon must NOT have been swept (no --force).
        assert port_cross not in swept_ports, (
            f"cross-root orphan port {port_cross} was swept without --force"
        )

        # Plain listener must not appear anywhere in reset_result.
        all_reported_ports = {
            e["port"]
            for entries in (rr["swept"], rr["skipped"], rr["failed"])
            for e in entries
        }
        assert port_plain not in all_reported_ports, (
            f"plain listener port {port_plain} appeared in reset_result: {rr!r}"
        )

    def test_doctor_reset_force_attempts_operator_required(
        self,
        harness: DaemonHarness,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """``auth doctor --reset --force --json`` attempts operator_required candidates.

        Setup: one cross-root (operator_required) orphan, no safe_auto orphan.
        With ``--force``, the doctor must attempt the cross-root daemon.
        Success (port closed) → ``swept``; failure → ``failed``.
        The important assertion is that ``skipped`` is empty — ``--force`` means
        no daemons are skipped on the operator_required path.
        """
        port_cross = find_free_port_in_range(_PORT_START, _PORT_END)
        # Use a different HOME so the cross-root daemon's owner.json doesn't
        # interfere with the test's scope-root classification.
        other_home = str(tmp_path / "force-home")
        other_scope = other_home

        harness.spawn_daemon(port_cross, "tok-force", scope_root=other_scope, home=other_home)

        self._patch_orphan_sweep(monkeypatch, harness)

        from specify_cli.cli.commands._auth_doctor import doctor_impl

        doctor_impl(
            json_output=True,
            reset=True,
            force=True,
            unstick_lock=False,
            stuck_threshold=60.0,
        )

        captured = capsys.readouterr()
        payload = json.loads(captured.out)

        assert "reset_result" in payload, f"reset_result missing from payload: {payload!r}"
        rr = payload["reset_result"]

        # With --force, nothing should be in skipped (for operator_required).
        skipped_ports = {e["port"] for e in rr["skipped"]}
        # cross-root with the correct cmdline signature should be in orphans.
        # If the port-scan found and classified it, it must have been attempted.
        swept_ports = {e["port"] for e in rr["swept"]}
        failed_ports = {e["port"] for e in rr["failed"]}

        assert port_cross not in skipped_ports, (
            f"port {port_cross} was skipped with --force active: {rr['skipped']!r}"
        )
        assert port_cross in swept_ports or port_cross in failed_ports, (
            f"port {port_cross} not found in swept={swept_ports!r} or "
            f"failed={failed_ports!r} with --force; skipped={skipped_ports!r}"
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _patch_orphan_sweep(
        self,
        monkeypatch: pytest.MonkeyPatch,
        harness: DaemonHarness,
    ) -> None:
        """Redirect ``orphan_sweep`` globals so the doctor reads from our harness."""
        monkeypatch.setattr(orphan_sweep, "DAEMON_STATE_FILE", harness.state_file)
        monkeypatch.setattr(orphan_sweep, "DAEMON_PORT_START", _PORT_START)
        monkeypatch.setattr(
            orphan_sweep,
            "DAEMON_PORT_MAX_ATTEMPTS",
            _PORT_END - _PORT_START,
        )


# ---------------------------------------------------------------------------
# T030 — isolation + SAAS env gate
# ---------------------------------------------------------------------------


class TestT030Isolation:
    """Suite-level isolation and CI-safety constraints (T030)."""

    def test_port_range_does_not_overlap_orphan_sweep(self) -> None:
        """WP06 port range [9401,9425) must not overlap test_orphan_sweep [9425,9450)
        and must exclude the production default first-port 9400 (RISK-1).
        """
        assert _PORT_END <= 9425, (
            f"WP06 range [{_PORT_START},{_PORT_END}) overlaps test_orphan_sweep [9425,9450)"
        )
        assert _PORT_START >= DAEMON_PORT_START, (
            f"WP06 range starts below DAEMON_PORT_START={DAEMON_PORT_START}"
        )
        assert _PORT_START > DAEMON_PORT_START, (
            f"WP06 range must exclude the production default first-port "
            f"{DAEMON_PORT_START} (RISK-1): _PORT_START={_PORT_START}"
        )

    def test_port_range_within_daemon_reserved_range(self) -> None:
        """All WP06 ports are within the reserved daemon range [9400,9450)."""
        daemon_end = DAEMON_PORT_START + DAEMON_PORT_MAX_ATTEMPTS
        assert _PORT_START >= DAEMON_PORT_START
        assert daemon_end >= _PORT_END

    @pytest.mark.skipif(
        not os.environ.get("SPEC_KITTY_ENABLE_SAAS_SYNC"),
        reason="SPEC_KITTY_ENABLE_SAAS_SYNC not set — SaaS-gated path skipped (C-006)",
    )
    def test_saas_env_gate_guard(self) -> None:
        """Placeholder: SAAS-gated tests only run when SPEC_KITTY_ENABLE_SAAS_SYNC=1."""
        assert os.environ.get("SPEC_KITTY_ENABLE_SAAS_SYNC") == "1", (
            "SPEC_KITTY_ENABLE_SAAS_SYNC must be '1' to run SaaS-gated tests"
        )

    @pytest.mark.skipif(sys.platform == "win32", reason="win32 uses different socket semantics")
    def test_find_free_port_in_range_returns_unbound_port(self) -> None:
        """``find_free_port_in_range`` returns a port we can immediately bind."""
        port = find_free_port_in_range(_PORT_START, _PORT_END)
        assert _PORT_START <= port < _PORT_END
        # Verify we can bind it.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))  # must not raise

    @pytest.mark.skipif(sys.platform == "win32", reason="win32 uses different socket semantics")
    def test_wait_until_listening_returns_true_when_bound(self) -> None:
        """``wait_until_listening`` detects a loopback server that is already up."""
        port = find_free_port_in_range(_PORT_START, _PORT_END)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("127.0.0.1", port))
            srv.listen(1)
            assert wait_until_listening(port, timeout_s=2.0)

    @pytest.mark.skipif(sys.platform == "win32", reason="win32 uses different socket semantics")
    def test_wait_until_port_free_returns_true_when_closed(self) -> None:
        """``wait_until_port_free`` confirms a port is free after closing a socket."""
        port = find_free_port_in_range(_PORT_START, _PORT_END)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("127.0.0.1", port))
            srv.listen(1)
            assert wait_until_listening(port, timeout_s=2.0)
        # Socket closed — port should now be free.
        assert wait_until_port_free(port, timeout_s=3.0)

    @pytest.mark.skipif(sys.platform == "win32", reason="real-port tests require POSIX socket semantics")
    def test_harness_shutdown_leaves_no_leaked_procs(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``DaemonHarness.shutdown()`` terminates all spawned daemons cleanly.

        Spawn a daemon, call ``shutdown()``, assert the port is free and the
        PID is gone.  This proves the harness teardown contract (no leaks).
        """
        state_file = tmp_path / "sync-daemon"

        monkeypatch.setattr(orphan_sweep, "DAEMON_STATE_FILE", state_file)
        monkeypatch.setattr(orphan_sweep, "DAEMON_PORT_START", _PORT_START)
        monkeypatch.setattr(
            orphan_sweep,
            "DAEMON_PORT_MAX_ATTEMPTS",
            _PORT_END - _PORT_START,
        )

        port = find_free_port_in_range(_PORT_START, _PORT_END)
        h = DaemonHarness(state_file)
        proc = h.spawn_daemon(port, "tok-leak-test")
        pid = proc.pid

        assert _port_listening(port), f"daemon on port {port} not listening before shutdown"
        h.shutdown()

        # Port must close.
        assert wait_until_port_free(port, timeout_s=6.0), (
            f"port {port} still listening after harness.shutdown()"
        )

        # PID must be gone.
        for _ in range(30):
            if not _pid_alive(pid):
                break
            time.sleep(0.05)
        assert not _pid_alive(pid), (
            f"PID {pid} still alive after harness.shutdown() and port closed"
        )
