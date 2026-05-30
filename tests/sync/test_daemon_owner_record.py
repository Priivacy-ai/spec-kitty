"""Unit tests for ``specify_cli.sync.owner``.

Covers the DaemonOwnerRecord schema, atomic write/read round-trips,
mismatch detection across every D-3 field, orphan detection via dead
PID and missing executable, the C-002 invariant that orphan detection
never signals operator processes, and the health-endpoint redaction
contract (the token never appears in the response payload).

All tests run with a temp ``HOME`` so the canonical ``<sync_root>/daemon/``
directory is a per-test scratch space.
"""

from __future__ import annotations

import builtins
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.integration]



# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _scoped_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pin ``HOME`` (and the platform-equivalent on Windows) to ``tmp_path``.

    Every test in this file relies on ``<sync_root>/daemon/owner.json``
    landing under ``tmp_path``; the fixture is autouse so individual tests
    don't have to re-state the setup.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    # Windows uses LOCALAPPDATA via RuntimeRoot; mirror it for portability.
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    # Note: we intentionally do NOT reload ``specify_cli.sync.daemon`` here.
    # Module-reloading rebinds the dataclasses defined inside the module
    # which breaks ``isinstance`` checks in other tests that import the
    # same names. ``owner.py`` resolves paths lazily via ``_sync_root()``
    # so the new HOME takes effect without any reload.
    return tmp_path


def _build_record(**overrides: Any) -> Any:
    from specify_cli.sync.owner import DaemonOwnerRecord

    defaults: dict[str, Any] = {
        "pid": os.getpid(),
        "port": 9400,
        "token": "deadbeefcafebabe",
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


# ---------------------------------------------------------------------------
# Write / read round-trip + atomic-write invariant
# ---------------------------------------------------------------------------


def test_write_then_read_round_trip(_scoped_home: Path) -> None:
    from specify_cli.sync.owner import owner_record_path, read_owner_record, write_owner_record

    record = _build_record()
    written = write_owner_record(record)
    assert written == owner_record_path()
    assert written.exists()

    loaded = read_owner_record()
    assert loaded == record


def test_read_returns_none_when_missing(_scoped_home: Path) -> None:
    from specify_cli.sync.owner import read_owner_record

    assert read_owner_record() is None


def test_resolve_source_checkout_path_avoids_root_cli_import(
    _scoped_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Daemon owner construction must not import the root CLI package."""
    from specify_cli.sync import owner as owner_mod

    real_import = builtins.__import__

    def guarded_import(name: str, globals=None, locals=None, fromlist=(), level=0):
        if name == "specify_cli" and not fromlist:
            raise AssertionError("root CLI package import is not allowed here")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    assert owner_mod._resolve_source_checkout_path() == str(
        Path(owner_mod.__file__).resolve().parents[3]
    )


def test_read_returns_none_on_corrupt_json(_scoped_home: Path) -> None:
    from specify_cli.sync.owner import owner_record_path, read_owner_record

    path = owner_record_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not-valid-json{{{", encoding="utf-8")

    assert read_owner_record() is None


def test_atomic_write_leaves_no_temp_files(_scoped_home: Path) -> None:
    """The atomic write path must not accumulate ``.owner-*.tmp`` siblings."""
    from specify_cli.sync.owner import owner_record_path, write_owner_record

    # Write the record several times; if the atomic-replace path leaked
    # tempfiles we would see them pile up.
    for port in (9400, 9401, 9402):
        write_owner_record(_build_record(port=port))

    parent = owner_record_path().parent
    siblings = sorted(p.name for p in parent.iterdir())
    # Exactly one file — the canonical owner.json — and nothing else.
    assert siblings == ["owner.json"], f"unexpected files in daemon dir: {siblings}"


def test_atomic_write_cleans_temp_file_on_failure(
    _scoped_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If ``os.replace`` raises, the temp file must be removed."""
    from specify_cli.sync import owner as owner_mod

    record = _build_record()

    real_replace = os.replace

    def boom(src: Any, dst: Any) -> None:
        # Intentionally fail to exercise the cleanup branch.
        raise OSError("simulated replace failure")

    monkeypatch.setattr(owner_mod.os, "replace", boom)
    with pytest.raises(OSError, match="simulated replace failure"):
        owner_mod.write_owner_record(record)
    monkeypatch.setattr(owner_mod.os, "replace", real_replace)

    parent = owner_mod.owner_record_path().parent
    leftovers = [p.name for p in parent.iterdir() if p.name.startswith(".owner-")]
    assert leftovers == [], f"temp files leaked: {leftovers}"


# ---------------------------------------------------------------------------
# Redaction (health endpoint contract — C-006 / FR-006)
# ---------------------------------------------------------------------------


def test_redact_token_replaces_token_field(_scoped_home: Path) -> None:
    from specify_cli.sync.owner import redact_token

    record = _build_record(token="should-not-appear")
    view = redact_token(record)
    assert view is not None
    assert "token" in view
    assert view["token"] != "should-not-appear"
    # The placeholder is a fixed string; the actual value MUST NOT leak.
    assert "should-not-appear" not in json.dumps(view)


def test_redact_token_passes_none_through() -> None:
    from specify_cli.sync.owner import redact_token

    assert redact_token(None) is None


def test_health_endpoint_excludes_token(_scoped_home: Path) -> None:
    """Unit-test the ``handle_health`` payload without spinning up a server.

    Exercises the same code path the live HTTP handler uses, but reads the
    JSON the handler writes to its in-memory file. The token configured
    on the handler MUST appear in the top-level ``token`` field (existing
    health contract) but the ``owner.token`` field MUST be redacted.
    """

    from specify_cli.sync import daemon as daemon_mod
    from specify_cli.sync.owner import write_owner_record

    # Persist an owner record so the handler picks it up.
    owner = _build_record(token="leaked-secret-token")
    write_owner_record(owner)

    # Build a barebones handler instance that bypasses the network stack.
    handler = daemon_mod.SyncDaemonHandler.__new__(daemon_mod.SyncDaemonHandler)
    handler.daemon_token = "handler-token"
    captured: dict[str, Any] = {}

    def fake_send_json(status_code: int, payload: dict[str, Any]) -> None:
        captured["status"] = status_code
        captured["payload"] = payload

    handler._send_json = fake_send_json  # type: ignore[method-assign]

    # The runtime accessor reaches into background machinery we don't
    # care about here; stub it out so we just exercise the owner branch.
    fake_runtime = MagicMock()
    fake_runtime.background_service = None
    fake_runtime.get_websocket_status.return_value = "Offline"
    import specify_cli.sync.runtime as runtime_mod

    original_runtime: Any = runtime_mod._runtime
    runtime_mod._runtime = fake_runtime
    try:
        handler.handle_health()
    finally:
        runtime_mod._runtime = original_runtime

    assert captured["status"] == 200
    payload = captured["payload"]
    assert payload["token"] == "handler-token"
    assert "owner" in payload
    # The owner subtree MUST NOT contain the daemon's bearer token.
    rendered = json.dumps(payload["owner"])
    assert "leaked-secret-token" not in rendered
    assert payload["owner"]["token"] != "leaked-secret-token"


def test_health_endpoint_does_not_start_runtime(_scoped_home: Path) -> None:
    """Health must stay lightweight so daemon startup can report readiness fast."""

    from specify_cli.sync import daemon as daemon_mod

    handler = daemon_mod.SyncDaemonHandler.__new__(daemon_mod.SyncDaemonHandler)
    handler.daemon_token = "handler-token"
    captured: dict[str, Any] = {}

    def fake_send_json(status_code: int, payload: dict[str, Any]) -> None:
        captured["status"] = status_code
        captured["payload"] = payload

    handler._send_json = fake_send_json  # type: ignore[method-assign]

    import specify_cli.sync.runtime as runtime_mod

    original_runtime: Any = runtime_mod._runtime
    original_get_runtime = runtime_mod.get_runtime
    runtime_mod._runtime = None

    def fail_get_runtime() -> object:
        raise AssertionError("health endpoint must not start runtime")

    runtime_mod.get_runtime = fail_get_runtime
    try:
        handler.handle_health()
    finally:
        runtime_mod.get_runtime = original_get_runtime
        runtime_mod._runtime = original_runtime

    assert captured["status"] == 200
    payload = captured["payload"]
    assert payload["sync"]["running"] is False
    assert payload["websocket_status"] == "Offline"


# ---------------------------------------------------------------------------
# Mismatch detection (D-3 / FR-007)
# ---------------------------------------------------------------------------


def _fg_from_record(record: Any) -> dict[str, Any]:
    """Build a foreground-identity dict that matches *record* on D-3 fields."""
    return {
        "package_version": record.package_version,
        "executable_path": record.executable_path,
        "server_url": record.server_url,
        "auth_scope": record.auth_scope,
        "queue_db_path": record.queue_db_path,
    }


def test_mismatched_fields_returns_empty_when_aligned(_scoped_home: Path) -> None:
    from specify_cli.sync.owner import mismatched_fields

    record = _build_record()
    fg = _fg_from_record(record)
    assert mismatched_fields(record, fg) == []


def test_mismatched_fields_normalizes_executable_symlink(
    _scoped_home: Path, tmp_path: Path
) -> None:
    """pipx-style executable symlinks should not create split-brain mismatches."""
    from specify_cli.sync.owner import mismatched_fields

    symlink = tmp_path / Path(sys.executable).name
    try:
        symlink.symlink_to(Path(sys.executable))
    except OSError as exc:
        pytest.skip(f"symlink unavailable on this platform: {exc}")

    record = _build_record(executable_path=str(symlink))
    fg = _fg_from_record(record)
    fg["executable_path"] = str(Path(sys.executable).resolve())

    assert mismatched_fields(record, fg) == []


def test_dataclass_canonicalizes_executable_path(
    _scoped_home: Path, tmp_path: Path
) -> None:
    """Constructing a record with a symlink path stores the resolved target.

    This locks in the dataclass-level invariant so future callers cannot
    silently bypass normalization by constructing records directly.
    """
    symlink = tmp_path / Path(sys.executable).name
    try:
        symlink.symlink_to(Path(sys.executable))
    except OSError as exc:
        pytest.skip(f"symlink unavailable on this platform: {exc}")

    record = _build_record(executable_path=str(symlink))
    assert record.executable_path == str(Path(sys.executable).resolve())


def test_canonical_executable_path_falls_back_to_raw_when_resolve_fails(
    _scoped_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If :meth:`Path.resolve` raises, the raw string survives unchanged.

    Exercises the ``except (OSError, RuntimeError)`` branch of
    ``_canonical_executable_path`` — without this test the fallback is
    untested and a regression could silently swallow the bug fix.
    """
    from specify_cli.sync import owner as owner_module

    raw_path = "/no/such/python-that-will-not-resolve"

    real_resolve = Path.resolve

    def _exploding_resolve(self: Path, *args: Any, **kwargs: Any) -> Path:
        if str(self) == raw_path:
            raise OSError("simulated resolve failure")
        return real_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", _exploding_resolve)

    assert owner_module._canonical_executable_path(raw_path) == raw_path


def test_mismatched_fields_when_one_side_fails_to_resolve(
    _scoped_home: Path, tmp_path: Path
) -> None:
    """Resolution failure on one side must NOT produce a half-mutated compare.

    Regression test for the earlier non-atomic try/except where a successful
    resolve on the daemon side combined with a failed resolve on the foreground
    side produced a spurious mismatch. With dataclass-level canonicalization,
    both sides are pre-normalized at write time, so this scenario reduces to a
    plain string compare and the helper cannot be tricked into a half-state.
    """
    from specify_cli.sync.owner import mismatched_fields

    symlink = tmp_path / Path(sys.executable).name
    try:
        symlink.symlink_to(Path(sys.executable))
    except OSError as exc:
        pytest.skip(f"symlink unavailable on this platform: {exc}")

    record = _build_record(executable_path=str(symlink))
    fg = _fg_from_record(record)
    # Foreground stores a path that no longer exists on disk; the canonical
    # helper still resolves it lexically (or falls back to raw) without
    # contaminating the daemon-side value the way the old try/except could.
    bogus = "/nonexistent/path/that/cannot/be/resolved/python"
    fg["executable_path"] = bogus

    mismatches = mismatched_fields(record, fg)
    assert mismatches == ["executable_path"]


@pytest.mark.parametrize(
    "field, mutated_value",
    [
        ("package_version", "0.0.0-mismatch"),
        ("executable_path", "/no/such/python"),
        ("server_url", "https://other.example.com"),
        ("auth_scope", None),  # None vs non-None is a mismatch per D-3
        ("queue_db_path", "/tmp/some-other-queue.db"),
    ],
)
def test_mismatched_fields_detects_each_d3_field(
    _scoped_home: Path, field: str, mutated_value: Any
) -> None:
    from specify_cli.sync.owner import mismatched_fields

    record = _build_record()
    fg = _fg_from_record(record)
    fg[field] = mutated_value
    assert mismatched_fields(record, fg) == [field]


def test_check_daemon_owner_match_no_record_is_ok(_scoped_home: Path) -> None:
    from specify_cli.sync.owner import check_daemon_owner_match

    ok, diff = check_daemon_owner_match()
    assert ok is True
    assert diff == []


def test_check_daemon_owner_match_detects_mismatch(
    _scoped_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from specify_cli.sync import owner as owner_mod

    record = _build_record()
    owner_mod.write_owner_record(record)

    fg = _fg_from_record(record)
    fg["package_version"] = "9.9.9-test"
    monkeypatch.setattr(owner_mod, "compute_foreground_identity", lambda: fg)

    ok, diff = owner_mod.check_daemon_owner_match()
    assert ok is False
    assert diff == ["package_version"]


# ---------------------------------------------------------------------------
# Orphan detection (FR-010 / C-002)
# ---------------------------------------------------------------------------


def _spawn_then_reap_pid() -> int:
    """Spawn a short subprocess we own, wait for it to exit, return its PID.

    Using a process we explicitly spawn + reap is the C-002-safe way to
    test "dead PID" semantics — we never reach for an operator process.
    """
    proc = subprocess.Popen(  # noqa: S603 — controlled command
        [sys.executable, "-c", "import sys; sys.exit(0)"],
    )
    proc.wait(timeout=5)
    return proc.pid


def test_is_orphan_true_when_pid_dead(_scoped_home: Path) -> None:
    from specify_cli.sync.owner import is_orphan

    dead_pid = _spawn_then_reap_pid()
    record = _build_record(pid=dead_pid)
    assert is_orphan(record) is True


def test_is_orphan_true_when_executable_missing(
    _scoped_home: Path, tmp_path: Path
) -> None:
    from specify_cli.sync.owner import is_orphan

    # Copy the current interpreter to a temp path, point the record at
    # it, then delete the copy so the recorded executable_path is gone.
    fake_exec = tmp_path / "fake-python"
    shutil.copy(sys.executable, fake_exec)
    record = _build_record(pid=os.getpid(), executable_path=str(fake_exec))
    fake_exec.unlink()
    assert is_orphan(record) is True


def test_is_orphan_false_when_alive_and_executable_present(_scoped_home: Path) -> None:
    from specify_cli.sync.owner import is_orphan

    record = _build_record(pid=os.getpid(), executable_path=sys.executable)
    assert is_orphan(record) is False


def test_is_orphan_does_not_signal_operator_processes(
    _scoped_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-002: orphan detection MUST NOT call ``os.kill``.

    We patch ``os.kill`` to raise, then exercise both the dead-PID and
    missing-executable branches. If anything in the predicate reached for
    ``os.kill`` against the recorded operator process, the test would
    blow up loudly.
    """
    from specify_cli.sync import owner as owner_mod

    def never_called(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("orphan detection must not call os.kill (C-002)")

    monkeypatch.setattr("os.kill", never_called)
    # Also catch the same call through the owner module's binding, in
    # case future refactors localise the import.
    monkeypatch.setattr(owner_mod.os, "kill", never_called, raising=False)

    dead_pid = _spawn_then_reap_pid()
    assert owner_mod.is_orphan(_build_record(pid=dead_pid)) is True
    assert owner_mod.is_orphan(_build_record(executable_path="/no/such/exe")) is True


def test_list_orphan_records_returns_empty_when_no_record(_scoped_home: Path) -> None:
    from specify_cli.sync.owner import list_orphan_records

    assert list_orphan_records() == []


def test_list_orphan_records_returns_empty_when_healthy(_scoped_home: Path) -> None:
    from specify_cli.sync.owner import list_orphan_records, write_owner_record

    write_owner_record(_build_record(pid=os.getpid(), executable_path=sys.executable))
    assert list_orphan_records() == []


def test_list_orphan_records_returns_stale_record(_scoped_home: Path) -> None:
    from specify_cli.sync.owner import list_orphan_records, write_owner_record

    dead_pid = _spawn_then_reap_pid()
    record = _build_record(pid=dead_pid)
    write_owner_record(record)

    orphans = list_orphan_records()
    assert len(orphans) == 1
    assert orphans[0].pid == dead_pid


# ---------------------------------------------------------------------------
# remove_owner_record
# ---------------------------------------------------------------------------


def test_remove_owner_record_returns_false_when_absent(_scoped_home: Path) -> None:
    from specify_cli.sync.owner import remove_owner_record

    assert remove_owner_record() is False


def test_remove_owner_record_removes_when_present(_scoped_home: Path) -> None:
    from specify_cli.sync.owner import (
        owner_record_path,
        remove_owner_record,
        write_owner_record,
    )

    write_owner_record(_build_record())
    assert owner_record_path().exists()
    assert remove_owner_record() is True
    assert not owner_record_path().exists()


# ---------------------------------------------------------------------------
# build_record_for_current_process
# ---------------------------------------------------------------------------


def test_build_record_for_current_process_uses_identity(
    _scoped_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from specify_cli.sync import owner as owner_mod

    fake_identity: dict[str, Any] = {
        "package_version": "1.2.3",
        "executable_path": "/usr/bin/python-test",
        "source_checkout_path": "/some/path",
        "server_url": "https://example.test",
        "auth_principal": "alice@example.test",
        "auth_team": "team-a",
        "auth_scope": "https://example.test|alice@example.test|team-a",
        "queue_db_path": "/tmp/queue.db",
    }
    monkeypatch.setattr(owner_mod, "compute_foreground_identity", lambda: fake_identity)

    record = owner_mod.build_record_for_current_process(pid=4242, port=9410, token="t")
    assert record.pid == 4242
    assert record.port == 9410
    assert record.token == "t"
    assert record.package_version == "1.2.3"
    assert record.executable_path == "/usr/bin/python-test"
    assert record.source_checkout_path == "/some/path"
    assert record.server_url == "https://example.test"
    assert record.auth_principal == "alice@example.test"
    assert record.auth_team == "team-a"
    assert record.auth_scope == "https://example.test|alice@example.test|team-a"
    assert record.queue_db_path == "/tmp/queue.db"
    # Timestamp is ISO-8601 UTC.
    assert record.started_at.endswith("+00:00")


# ---------------------------------------------------------------------------
# T016: sync now refuses on daemon-owner mismatch (FR-002)
# ---------------------------------------------------------------------------


def _build_compute_foreground_for_split_brain() -> dict[str, Any]:
    """Helper: return a foreground identity that DIFFERS from the daemon record."""
    return {
        "package_version": "9.9.9-foreground",
        "executable_path": sys.executable,
        "source_checkout_path": str(Path(__file__).resolve().parents[2]),
        "server_url": "https://spec-kitty-dev.fly.dev",
        "auth_principal": "tester@example.com",
        "auth_team": "t-private",
        "auth_scope": "https://spec-kitty-dev.fly.dev|tester@example.com|t-private",
        "queue_db_path": str(Path.home() / ".spec-kitty" / "queues" / "queue-aaaaaaaa.db"),
    }


def test_sync_now_refuses_on_daemon_owner_mismatch(
    _scoped_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`sync now` MUST refuse with exit 2 when the boundary is incoherent.

    The refusal MUST happen BEFORE any DB write or SaaS flush. We assert
    this indirectly: the queue size is never read (no console output
    about syncing), and the call returns exit code 2.
    """
    from typer.testing import CliRunner

    from specify_cli.cli.commands.sync import app
    from specify_cli.sync import owner as owner_mod
    from specify_cli.sync.feature_flags import SAAS_SYNC_ENV_VAR

    monkeypatch.setenv(SAAS_SYNC_ENV_VAR, "1")

    # Write a daemon record whose package_version disagrees with the
    # foreground; sync now must refuse before any enqueue.
    record = _build_record(package_version="3.2.0-daemon")
    owner_mod.write_owner_record(record)

    # Force a split-brain identity so the preflight finds a mismatch.
    monkeypatch.setattr(
        "specify_cli.sync.owner.compute_foreground_identity",
        _build_compute_foreground_for_split_brain,
    )
    # Also stub the preflight's foreground-identity helper to surface the
    # same divergent values — the preflight reads via its own collector,
    # so we mock that path too.
    import specify_cli.sync.preflight as preflight_mod
    from specify_cli.sync.preflight import ForegroundIdentity

    def fake_collect(_repo_root: Path) -> ForegroundIdentity:
        return ForegroundIdentity(
            package_version="9.9.9-foreground",
            executable_path=Path(sys.executable),
            source_path=Path(__file__).resolve().parents[2],
            server_url="https://spec-kitty-dev.fly.dev",
            team_or_user="tester@example.com/t-private",
            queue_db_path=Path("/tmp/foreground-queue.db"),
            pid=os.getpid(),
        )

    monkeypatch.setattr(
        preflight_mod, "collect_foreground_identity", fake_collect
    )

    runner = CliRunner()
    result = runner.invoke(app, ["now"])
    assert result.exit_code == 2, result.stdout
    flat = " ".join(result.stdout.split())
    # The refusal banner names the gated command.
    assert "Refusing" in flat or "refused" in flat
    # And the rendered remediation references the boundary mismatch.
    assert "spec-kitty sync now" in flat or "mismatched" in flat


# ---------------------------------------------------------------------------
# T016: sync doctor and preflight agree on orphan detection
# ---------------------------------------------------------------------------


def test_sync_doctor_and_preflight_agree_on_orphan_detection(
    _scoped_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same orphan-record fixture must be detected by both code paths.

    `sync doctor`'s orphan section and `run_preflight`'s `orphan_records`
    both flow through `list_orphan_records()`; this test locks the
    invariant so a future refactor can't cause them to disagree.
    """
    from specify_cli.sync.owner import list_orphan_records, write_owner_record
    from specify_cli.sync.preflight import build_boundary_failure_set

    def _spawn_then_reap_pid_local() -> int:
        proc = subprocess.Popen(  # noqa: S603 — controlled command
            [sys.executable, "-c", "import sys; sys.exit(0)"],
        )
        proc.wait(timeout=5)
        return proc.pid

    dead_pid = _spawn_then_reap_pid_local()
    record = _build_record(pid=dead_pid)
    write_owner_record(record)

    # Path 1: list_orphan_records (used by sync doctor + sync status section).
    doctor_orphans = list_orphan_records()

    # Path 2: build_boundary_failure_set (used by run_preflight and the
    # sync status --check / --json surfaces).
    failure_set = build_boundary_failure_set(repo_root=Path.cwd())
    preflight_orphans = list(failure_set.orphan_records)

    # Both surfaces must surface the same set of orphan PIDs.
    doctor_pids = sorted(r.pid for r in doctor_orphans)
    preflight_pids = sorted(r.pid for r in preflight_orphans)
    assert doctor_pids == preflight_pids
    assert dead_pid in doctor_pids
